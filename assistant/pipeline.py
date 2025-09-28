import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import re
from unidecode import unidecode
from assistant.local_llm import generate_local_response
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import sqlite3

from assistant import config

# ==============================================================================
# PARTE 1: NORMALIZAÇÃO DAS TABELAS PARA REPRESENTAÇÃO
# ==============================================================================

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return unidecode(str(s)).lower().strip()

def build_thorr_table_representation(df: pd.DataFrame, name: str, base_text: str = "") -> str:
    relations = ""
    if name == 'buildings': relations = "Relacionada com: units (id_predio), typologies (id_predio)"
    elif name == 'units': relations = "Relacionada com: buildings (id_predio), units_updates (unidade_id)"
    elif name == 'typologies': relations = "Relacionada com: buildings (id_predio)"
    elif name == 'units_updates': relations = "Relacionada com: units (unidade_id)"
    
    parts = [
        f"TABELA: {name}",
        f"DESCRIÇÃO: {base_text} {relations}",
        f"COLUNAS: {', '.join(df.columns)}"
    ]
    return "\n".join(parts)

def load_data():
    dfs = {}
    for name, path in config.DATA_FILES.items():
        try:
            dfs[name] = pd.read_excel(path)
        except FileNotFoundError:
            print(f"AVISO: Arquivo não encontrado em '{path}'. Pulando...")
    return dfs

# ==============================================================================
# PARTE 2: CONSTRUINDO REPRESENTAÇÃO DAS TABELAS E ÍNDICE FAISS
# ==============================================================================

def setup_faiss_and_model(dfs, base_texts, model):
    table_representations = {name: build_thorr_table_representation(df, name, base_texts.get(name, "")) for name, df in dfs.items()}
    table_names = list(table_representations.keys())
    table_texts = [f"passage: {desc}" for desc in table_representations.values()]
    table_embeddings = model.encode(table_texts)
    index = faiss.IndexFlatL2(table_embeddings.shape[1])
    index.add(np.array(table_embeddings))
    return index, table_names, table_texts, table_embeddings

# ==============================================================================
# PARTE 2: A LÓGICA DE RECUPERAÇÃO
# ==============================================================================

def retrieve_tables_thorr(question, model, index, table_names, k=3):
    augmented_question = f"query: {question}"
    question_embedding = model.encode([augmented_question])
    _, indices = index.search(question_embedding, k)
    relevant_by_faiss = [table_names[i] for i in indices[0]]
    return relevant_by_faiss[:k]

#==============================================================================
# PARTE 3: A LÓGICA DE REFINAMENTO (THoRR: Refinement)
# ==============================================================================

def refine_tables_thorr(question: str, retrieved_tables: list, all_dfs: dict, model, top_k_columns: int = 20):
    refined_dfs = {}
    column_texts, column_refs = [], []
    
    for tname in retrieved_tables:
        df = all_dfs.get(tname)
        if df is None: continue
        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(5).tolist()
            text = f"passage: Tabela {tname}, Coluna {col}. Exemplos: {', '.join(sample_values)}"
            column_texts.append(text)
            column_refs.append((tname, col))
    
    if not column_texts: return {}
    
    column_embeddings = model.encode(column_texts)
    col_index = faiss.IndexFlatL2(column_embeddings.shape[1])
    col_index.add(np.array(column_embeddings))
    
    question_embedding = model.encode([f"query: {question}"])
    _, I = col_index.search(question_embedding, top_k_columns)
    
    selected_cols_per_table = {}
    for idx in I[0]:
        tname, col = column_refs[idx]
        if tname not in selected_cols_per_table:
            selected_cols_per_table[tname] = set()
        selected_cols_per_table[tname].add(col)
    
    key_columns = config.KEY_COLUMNS

    for tname in selected_cols_per_table.keys():
        original_df_cols = all_dfs[tname].columns
        for key_col in key_columns:
            if key_col in original_df_cols:
                selected_cols_per_table[tname].add(key_col)

    for tname, cols in selected_cols_per_table.items():
        df = all_dfs[tname]
        filtered_df = df[list(cols)].copy()
        for c in filtered_df.columns:
            if pd.api.types.is_numeric_dtype(filtered_df[c]):
                filtered_df.loc[:, c] = filtered_df[c].fillna(0)
            else:
                filtered_df.loc[:, c] = filtered_df[c].fillna('')
        refined_dfs[tname] = filtered_df
    
    return refined_dfs

# ==============================================================================
# PARTE 4: INTEGRAÇÃO COM O LLM (ChatGPT)
# ==============================================================================

def generate_sql_query_from_refined(question: str, refined_dfs: dict) -> str:
    
    schema_string = ""
    # ... (código que constrói schema_string permanece o mesmo) ...

    system_message = config.SQL_GENERATION_SYSTEM_PROMPT
    user_message = (f"Esquema de banco de dados:\n{schema_string}\n\n"
                    f"Pergunta do usuário: {question}\n\n"
                    "Consulta SQL:")
    
    print("-" * 50)
    print("Conteúdo do prompt enviado ao ChatGPT:")
    print("-" * 50)
    print(user_message)
    print("-" * 50)

    try:
        # 1. PASSO CORRIGIDO: CHAMA A FUNÇÃO LLM PARA OBTER O TEXTO!
        sql_query = generate_local_response(system_message, user_message, config.CHAT_MODEL)
        
        # 2. Limpeza Agressiva do Markdown (como discutimos)
        sql_query = sql_query.strip()
        if sql_query.startswith('```'):
            sql_query = sql_query.lstrip('` \n')
        if sql_query.endswith('```'):
            sql_query = sql_query.rstrip('` \n')
            
        # Garante que qualquer tag "sql" inicial seja removida
        if sql_query.lower().startswith('sql'):
             sql_query = sql_query[3:].strip()
             
        return sql_query.strip()

    except Exception as e:
        # Se houver qualquer erro, incluindo falha ao chamar o generate_local_response
        return f"Ocorreu um erro ao gerar a consulta SQL: {e}"
def run_sql_pipeline(question: str, model, index, table_names, all_dfs, verbose: bool = False):
    """
    Executa o pipeline completo de Text-to-SQL e opcionalmente imprime os passos de debug.
    """
    if verbose:
        print("=" * 50)
        print(f"DEBUG - Etapa 1: Recuperação de Tabelas")
        print(f"Pergunta: '{question}'")
    
    retrieved_tables = retrieve_tables_thorr(question, model, index, table_names)
    
    if verbose:
        print(f"Tabelas recuperadas: {retrieved_tables}")
        print("=" * 50)

    if verbose:
        print("\n" + "=" * 50)
        print(f"DEBUG - Etapa 2: Refinamento de Colunas")

    refined_data = refine_tables_thorr(question, retrieved_tables, all_dfs, model)
    
    if verbose:
        print("Dados refinados (tabelas e colunas):")
        for name, data in refined_data.items():
            print(f"\n--- Tabela '{name}' ---")
            print(data.head(2))
        print("=" * 50)
    
    if verbose:
        print("\n" + "=" * 50)
        print(f"DEBUG - Etapa 3: Geração da Consulta SQL")

    sql_query = generate_sql_query_from_refined(question, refined_data)
    
    if verbose:
        print(f"\nConsulta SQL gerada:\n{sql_query}")
        print("=" * 50)

    return sql_query

def handle_data_assistance(question: str, all_dfs: dict) -> str:
    # A lógica para construir o esquema de dados permanece a mesma
    schema_string = ""
    for table_name, df in all_dfs.items():
        schema_string += f"Tabela: {table_name}\n"
        schema_string += f"- Colunas: {', '.join(df.columns)}\n"
        sample_values = df.head(1).to_string(index=False)
        schema_string += f"- Exemplo de dados: {sample_values}\n\n"

    system_message = """Você é o assistente Thorr. Sua tarefa é responder perguntas sobre o esquema de banco de dados e os dados que você contém de forma clara e conversacional. Não invente dados numéricos. Responda apenas com base no esquema fornecido."""

    user_message = f"Esquema de banco de dados:\n{schema_string}\n\nPergunta do usuário: {question}\n\nResposta:"

    try:
        # Substituímos a chamada da API da OpenAI pela função do modelo local
        return generate_local_response(system_message, user_message, config.CHAT_MODEL)
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao processar sua solicitação sobre o esquema dos dados: {e}"

# ==============================================================================
# TRECHO DE EXECUÇÃO DE EXEMPLO (PARA TESTE)
# ==============================================================================

# if __name__ == "__main__":
#     print("Iniciando o carregamento dos dados...")
#     # ALTERADO: load_data agora só retorna os dataframes
#     dfs = load_data()
#     print("Dados carregados com sucesso.\n")
    
#     print(f"Carregando o modelo '{config.EMBEDDING_MODEL}'...")
#     # ALTERADO: Nome do modelo vem do config
#     model = SentenceTransformer(config.EMBEDDING_MODEL)
#     print("Modelo carregado.\n")
    
#     print("Configurando FAISS...")
#     # ALTERADO: Passa config.BASE_TEXTS para a função
#     index, table_names, _, _ = setup_faiss_and_model(dfs, config.BASE_TEXTS, model)
#     print("Configuração FAISS concluída.\n")

#     question = "Quantas unidades a incorporadora melnick even tem? "
#     print("=" * 50)
#     print(f"DEBUG - Etapa 1: Recuperação de Tabelas")
#     print(f"Pergunta: '{question}'")
#     retrieved_tables = retrieve_tables_thorr(question, model, index, table_names)
#     print(f"Tabelas recuperadas: {retrieved_tables}")
#     print("=" * 50)
    
#     print("\n" + "=" * 50)
#     print(f"DEBUG - Etapa 2: Refinamento de Colunas")
#     refined_data = refine_tables_thorr(question, retrieved_tables, dfs, model)
#     print("Dados refinados (tabelas e colunas):")
#     for name, data in refined_data.items():
#         print(f"\n--- Tabela '{name}' ---")
#         print(data.head(2))
#     print("=" * 50)
    
#     print("\n" + "=" * 50)
#     print(f"DEBUG - Etapa 3: Geração da Consulta SQL")
#     sql_query = generate_sql_query_from_refined(question, refined_data)
#     print(f"\nConsulta SQL gerada:\n{sql_query}")
#     print("=" * 50)