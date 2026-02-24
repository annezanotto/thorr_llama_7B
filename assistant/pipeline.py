import pandas as pd
import numpy as np
import faiss
import re
import difflib
from unidecode import unidecode

from assistant.local_llm import generate_local_response
from assistant import config


# ==============================================================================
# UTILITÁRIOS
# ==============================================================================

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return unidecode(str(s)).lower().strip()


def safe_replace_word(sql_query: str, word: str, replacement: str) -> str:
    """Substitui palavra apenas quando isolada."""
    return re.sub(rf"\b{re.escape(word)}\b", replacement, sql_query)


def fix_invalid_columns(sql_query: str, all_dfs: dict) -> str:
    """
    Corrige colunas inexistentes com base nas colunas reais dos DataFrames.
    Usa substituição segura via regex.
    """
    all_columns = {}
    for table, df in all_dfs.items():
        for col in df.columns:
            all_columns[col] = table

    tokens = re.findall(r"\b\w+\b", sql_query)

    for token in tokens:
        # Caso tabela.coluna
        if "." in token:
            parts = token.split(".", 1)
            if len(parts) == 2:
                table, col = parts
                if table in all_dfs and col not in all_dfs[table].columns:
                    match = difflib.get_close_matches(col, all_dfs[table].columns, n=1)
                    if match:
                        sql_query = safe_replace_word(sql_query, col, match[0])

        # Caso coluna isolada
        elif token in all_columns:
            sql_query = safe_replace_word(
                sql_query,
                token,
                f"{all_columns[token]}.{token}"
            )

    return sql_query


# ==============================================================================
# CONSTRUÇÃO DAS REPRESENTAÇÕES
# ==============================================================================

def build_table_representation(df: pd.DataFrame, name: str, base_text: str = "") -> str:
    description = f"{base_text}"
    return (
        f"TABELA: {name}\n"
        f"DESCRIÇÃO: {description}\n"
        f"COLUNAS: {', '.join(df.columns)}"
    )


def setup_faiss_index(dfs: dict, base_texts: dict, model):
    """
    Cria índice FAISS usando Inner Product + normalização.
    """
    table_representations = {
        name: build_table_representation(df, name, base_texts.get(name, ""))
        for name, df in dfs.items()
    }

    table_names = list(table_representations.keys())
    texts = [f"passage: {desc}" for desc in table_representations.values()]

    embeddings = model.encode(texts)
    embeddings = np.array(embeddings).astype("float32")

    # Normaliza para similaridade cosseno
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return index, table_names

# ==============================================================================
# RETRIEVAL DE TABELAS
# ==============================================================================

def retrieve_tables(question, model, index, table_names, k=3):
    question_embedding = model.encode([f"query: {question}"])
    question_embedding = np.array(question_embedding).astype("float32")
    faiss.normalize_L2(question_embedding)

    _, indices = index.search(question_embedding, k)
    return [table_names[i] for i in indices[0]]


# ==============================================================================
# REFINAMENTO DE COLUNAS
# ==============================================================================

def refine_tables(question: str, retrieved_tables: list, all_dfs: dict, model, top_k_columns: int = 5):
    refined_dfs = {}
    question_embedding = model.encode([f"query: {question}"])
    question_embedding = np.array(question_embedding).astype("float32")
    faiss.normalize_L2(question_embedding)

    for tname in retrieved_tables:
        df = all_dfs.get(tname)
        if df is None or df.empty:
            continue

        column_texts = []
        column_names = []

        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(5).tolist()
            text = f"passage: Tabela {tname}, Coluna {col}. Exemplos: {', '.join(sample_values)}"
            column_texts.append(text)
            column_names.append(col)

        if not column_texts:
            continue

        col_embeddings = model.encode(column_texts)
        col_embeddings = np.array(col_embeddings).astype("float32")
        faiss.normalize_L2(col_embeddings)

        col_index = faiss.IndexFlatIP(col_embeddings.shape[1])
        col_index.add(col_embeddings)

        _, indices = col_index.search(question_embedding, top_k_columns)

        selected_cols = {column_names[i] for i in indices[0]}

        # Adiciona colunas-chave do config
        for key_col in config.KEY_COLUMNS:
            if key_col in df.columns:
                selected_cols.add(key_col)

        if not selected_cols:
            continue

        filtered_df = df[list(selected_cols)].copy()

        # Preenche NaN
        for c in filtered_df.columns:
            if pd.api.types.is_numeric_dtype(filtered_df[c]):
                filtered_df[c] = filtered_df[c].fillna(0)
            else:
                filtered_df[c] = filtered_df[c].fillna("")

        refined_dfs[tname] = filtered_df

    return refined_dfs

# ==============================================================================
# GERAÇÃO DE SQL
# ==============================================================================

def generate_sql_query_from_refined(question: str, refined_dfs: dict, all_dfs: dict, debug=False):

    schema_string = ""

    for table_name, df in refined_dfs.items():
        schema_string += f"Tabela: {table_name}\n"
        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(3).tolist()
            schema_string += f"- Coluna '{col}': Exemplos: {sample_values}\n"
        schema_string += "\n"

    schema_string += config.TABLE_RELATIONS

    system_message = config.SQL_GENERATION_SYSTEM_PROMPT

    user_message = (
        f"### ESQUEMA DE BANCO DE DADOS ###\n"
        f"{schema_string}\n"
        f"### PERGUNTA ###\n{question}\n"
    )

    if debug:
        print("\n========== PROMPT ==========")
        print(user_message)
        print("============================\n")

    sql_query = generate_local_response(
        system_message,
        user_message,
        config.CHAT_MODEL
    )

    # Limpeza robusta
    sql_query = sql_query.strip()

    if "```" in sql_query:
        sql_query = sql_query.split("```")[1]

    if sql_query.lower().startswith("sql"):
        sql_query = sql_query[3:].strip()

    sql_query = fix_invalid_columns(sql_query, all_dfs)

    return sql_query.strip()

# ==============================================================================
# PIPELINE COMPLETO
# ==============================================================================

def run_sql_pipeline(question: str, model, index, table_names, all_dfs, debug=False):

    if debug:
        print("\n=== ETAPA 1: RETRIEVAL ===")

    retrieved_tables = retrieve_tables(question, model, index, table_names)

    if debug:
        print("Tabelas recuperadas:", retrieved_tables)

    if debug:
        print("\n=== ETAPA 2: REFINAMENTO ===")

    refined_data = refine_tables(question, retrieved_tables, all_dfs, model)

    if debug:
        for name, df in refined_data.items():
            print(f"\nTabela refinada: {name}")
            print(df.head())

    if debug:
        print("\n=== ETAPA 3: GERAÇÃO SQL ===")

    sql_query = generate_sql_query_from_refined(
        question,
        refined_data,
        all_dfs,
        debug=debug
    )

    if debug:
        print("\nSQL Gerado:\n", sql_query)

    return sql_query
# ==============================================================================
# PARTE 2: CONSTRUÇÃO DO CONTEXTO (ESQUEMA + AMOSTRAS)
# ==============================================================================

# def generate_full_schema_with_samples(all_dfs: dict) -> str:
#     """
#     Cria a representação textual do esquema e 3 exemplos de linhas por tabela.
#     """
#     # 1. Construção da seção de ESQUEMA
#     schema_section = "========================\nESQUEMA (SQLite)\n========================\n\n"
#     for table_name, df in all_dfs.items():
#         schema_section += f"Tabela: {table_name}\n"
#         for col in df.columns:
#             suffix = " (PK/FK)" if col.lower().endswith('_id') or col.lower() == 'id' else ""
#             schema_section += f"- {col}{suffix}\n"
#         schema_section += "\n"

#     # 2. Construção da seção de EXEMPLOS DE DADOS
#     samples_section = "========================\nEXEMPLOS DE DADOS (3 linhas por tabela)\n========================\n\n"
#     for table_name, df in all_dfs.items():
#         samples_section += f"{table_name} (exemplos)\n"
#         # Pega as 3 primeiras linhas e formata como dicionários
#         top_3 = df.head(3).to_dict(orient='records')
#         for i, row in enumerate(top_3, 1):
#             # repr(v) garante que strings fiquem entre aspas e números fiquem puros
#             row_str = ", ".join([f"{k}={repr(v)}" for k, v in row.items()])
#             samples_section += f"{i}) ({row_str})\n"
#         samples_section += "\n"

#     return schema_section + samples_section

# # ==============================================================================
# # PARTE 3: GERAÇÃO DE SQL (TEXT-TO-SQL)
# # ==============================================================================

# def generate_sql_query_from_total(question: str, all_dfs: dict) -> str:
#     """
#     Gera a query SQL consolidando regras rígidas, esquema e exemplos.
#     """
#     # 1. Recupera o Esquema e Amostras (3 linhas por tabela)
#     full_schema_context = generate_full_schema_with_samples(all_dfs)

#     # 2. Define as Relações de Join
#     relations = (
#         "========================\nRELAÇÕES (CHAVES PARA JOIN)\n========================\n"
#         "- Clientes.cliente_id = Contratos.cliente_id\n"
#         "- ProdutosFinanciamento.produto_id = Contratos.produto_id\n"
#         "- Contratos.contrato_id = Parcelas.contrato_id\n"
#         "- Contratos.contrato_id = Garantias.contrato_id\n"
#         "- Parcelas.parcela_id = PagamentosRealizados.parcela_id\n\n"
#     )

#     # 3. Regras do Config (Suas 9 regras cruciais)
#     system_rules = config.SQL_GENERATION_SYSTEM_PROMPT

#     # 4. Montagem do prompt com "Guardrails" (Proteções)
#     # Colocamos a Pergunta e a Instrução de "SQL PURO" no final para evitar alucinações
#     user_message = (
#         f"{full_schema_context}\n"
#         f"{relations}\n"
#         "========================\n"
#         "REGRAS OBRIGATÓRIAS\n"
#         "========================\n"
#         f"{system_rules}\n\n"
#         "### EXEMPLO DE ESTILO ###\n"
#         "Pergunta: Quais clientes têm renda mensal acima de 10.000?\n"
#         "SQL: SELECT cliente_id, nome, cpf, renda_mensal FROM Clientes WHERE renda_mensal > 10000 ORDER BY renda_mensal DESC;\n\n"
#         "========================\n"
#         "PERGUNTA DO USUÁRIO\n"
#         "========================\n"
#         f"{question}\n\n"
#         "Gere o SQL seguindo as regras (sem ';' e com prefixos):"
#     )

#     print("-" * 30 + " PROMPT ENVIADO " + "-" * 30)
#     print(user_message)

#     try:
#         # Passamos o system_rules como instrução de sistema no modelo
#         sql_query = generate_local_response(system_rules, user_message, config.CHAT_MODEL)
        
#         # Limpeza agressiva de Markdown e quebras de linha
#         sql_query = sql_query.strip().replace('```sql', '').replace('```', '').split(';')[0].strip()
        
#         # Garante que não haja ponto e vírgula (Regra 9)
#         sql_query = sql_query.replace(';', '')

#         # Correção final de colunas
#         sql_query = fix_invalid_columns(sql_query, all_dfs)
        
#         return sql_query

#     except Exception as e:
#         return f"-- Erro na geração: {e}"

# ==============================================================================
# PARTE 4: ASSISTÊNCIA DE DADOS (Conversacional sobre o esquema)
# ==============================================================================

def handle_data_assistance(question: str, all_dfs: dict) -> str:
    """Responde dúvidas sobre o que há no banco de dados sem gerar SQL."""
    schema_string = ""
    for table_name, df in all_dfs.items():
        schema_string += f"Tabela: {table_name}\n"
        schema_string += f"- Colunas: {', '.join(df.columns)}\n\n"

    system_message = "Você é o assistente Thorr. Explique o esquema de dados de forma clara e honesta."
    user_message = f"Esquema de banco de dados:\n{schema_string}\n\nPergunta: {question}"

    try:
        return generate_local_response(system_message, user_message, config.CHAT_MODEL)
    except Exception as e:
        return f"Erro na assistência: {e}"