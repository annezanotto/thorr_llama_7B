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
import difflib
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

def refine_tables_thorr(question: str, retrieved_tables: list, all_dfs: dict, model, top_k_columns: int = 6):
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
    
    if not column_texts:
        return {}

    selected_cols_per_table = {}

    for tname in retrieved_tables:
        df = all_dfs.get(tname)
        if df is None:
            continue

        # monta textos de exemplo para cada coluna da tabela
        cols_texts, cols_refs = [], []
        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(5).tolist()
            cols_texts.append(f"passage: Tabela {tname}, Coluna {col}. Exemplos: {', '.join(sample_values)}")
            cols_refs.append(col)

        # gera embeddings só dessa tabela
        if not cols_texts:
            continue
        col_embeddings = model.encode(cols_texts)
        col_index = faiss.IndexFlatL2(col_embeddings.shape[1])
        col_index.add(np.array(col_embeddings))

        # busca as colunas mais relevantes dessa tabela
        question_embedding = model.encode([f"query: {question}"])
        _, I = col_index.search(question_embedding, top_k_columns)

        # guarda as colunas selecionadas
        selected_cols_per_table[tname] = {cols_refs[i] for i in I[0]}

    # adiciona colunas-chave (id_predio, etc.)
    key_columns = config.KEY_COLUMNS
    for tname in selected_cols_per_table.keys():
        original_df_cols = all_dfs[tname].columns
        for key_col in key_columns:
            if key_col in original_df_cols:
                selected_cols_per_table[tname].add(key_col)

    # monta os dataframes refinados
    refined_dfs = {}
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
# PARTE 4: INTEGRAÇÃO COM O LLM PARA GERAÇÃO DE SQL
# ==============================================================================

def fix_invalid_columns(sql_query: str, refined_dfs: dict) -> str:
    """Corrige colunas inexistentes ou mal escritas com base nas colunas reais dos DataFrames."""
    all_columns = {}
    for table, df in refined_dfs.items():
        for col in df.columns:
            all_columns[col] = table

    words = sql_query.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
    for word in words:
        if '.' in word:
            table, col = word.split('.', 1)
            if table in refined_dfs and col not in refined_dfs[table].columns:
                match = difflib.get_close_matches(col, refined_dfs[table].columns, n=1)
                if match:
                    sql_query = sql_query.replace(col, match[0])
        else:
            # Corrige colunas sem prefixo
            if word in all_columns:
                sql_query = sql_query.replace(word, f"{all_columns[word]}.{word}")
    return sql_query


# --------------------------------------------------
 #Função principal: gera a query SQL a partir dos dados refinados
# --------------------------------------------------
def generate_sql_query_from_refined(question: str, refined_dfs: dict) -> str:
    schema_string = ""
    for table_name, df in refined_dfs.items():
        schema_string += f"Tabela: {table_name}\n"
        
        col_examples = []
        for col in df.columns:
            try:
                sample_values = df[col].dropna().head(3).astype(str).tolist()
            except Exception:
                sample_values = ["Dados indisponíveis"]
            col_examples.append(f"- Coluna '{col}': Exemplo(s): {sample_values}")
        
        schema_string += "\n".join(col_examples) + "\n\n"

    # adiciona as relações só uma vez
    schema_string += "### RELAÇÕES ENTRE TABELAS ###\n"
    schema_string += (
        "- buildings.id_predio = typologies.id_predio\n"
        "- buildings.id_predio = units.id_predio\n"
        "- typologies.id_tipologia = units.id_tipologia\n"
        "- units.id_unidade = units_updates.id_unidade\n\n"
    )

    # 🔹 Instruções adicionais e exemplos (few-shot)
    guidance_examples = """

### EXEMPLOS ###
Pergunta: Quantos edifícios estão localizados na cidade de porto alegre?
SQL: SELECT COUNT(*) FROM buildings WHERE cidade_endereço = 'porto alegre';

Pergunta: Qual a área média das unidades no bairro jardim europa?
SQL: SELECT AVG(units.area_privativa)
FROM units
JOIN buildings ON units.id_predio = buildings.id_predio
WHERE buildings.bairro_endereço = 'jardim europa';

Pergunta: Qual a quantidade de prédios da incorporadora melnick even?
SQL: SELECT COUNT(*) FROM buildings WHERE incorporadora_nome = 'melnick even';
"""


    #  Cria o prompt delimitado
    system_message = config.SQL_GENERATION_SYSTEM_PROMPT
    user_message = (
        f"{guidance_examples}\n\n"
        "### ESQUEMA DE BANCO DE DADOS ###\n"
        f"{schema_string}\n"
        "### PERGUNTA DO USUÁRIO ###\n"
        f"{question}\n\n"
        "### INSTRUÇÃO ###\n"
    )

    print("-" * 50)
    print("Conteúdo do prompt enviado ao modelo:")
    print("-" * 50)
    print(user_message)
    print("-" * 50)

    try:
        # 🔹 Geração local com modelo
        sql_query = generate_local_response(system_message, user_message, config.CHAT_MODEL)
        
        # 🔹 Limpeza de markdown e prefixos indesejados
        sql_query = sql_query.strip()
        if sql_query.startswith('```'):
            sql_query = sql_query.lstrip('` \n')
        if sql_query.endswith('```'):
            sql_query = sql_query.rstrip('` \n')
        if sql_query.lower().startswith('sql'):
            sql_query = sql_query[3:].strip()

        # 🔹 Correção automática de colunas inválidas
        sql_query = fix_invalid_columns(sql_query, refined_dfs)
        
        return sql_query.strip()

    except Exception as e:
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
    schema_string = ""
    for table_name, df in all_dfs.items():
        schema_string += f"Tabela: {table_name}\n"
        schema_string += f"- Colunas: {', '.join(df.columns)}\n"
        sample_values = df.head(1).to_string(index=False)
        schema_string += f"- Exemplo de dados: {sample_values}\n\n"

    system_message = """Você é o assistente Thorr. Sua tarefa é responder perguntas sobre o esquema de banco de dados e os dados que você contém de forma clara e conversacional. Não invente dados numéricos. Responda apenas com base no esquema fornecido."""

    user_message = f"Esquema de banco de dados:\n{schema_string}\n\nPergunta do usuário: {question}\n\nResposta:"

    try:
        return generate_local_response(system_message, user_message, config.CHAT_MODEL)
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao processar sua solicitação sobre o esquema dos dados: {e}"

