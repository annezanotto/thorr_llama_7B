import pandas as pd
import numpy as np
from unidecode import unidecode
from assistant.local_llm import generate_local_response
import difflib
from assistant import config

# ==============================================================================
# PARTE 1: UTILITÁRIOS E CORREÇÕES
# ==============================================================================

def normalize_text(s: str) -> str:
    if s is None:
        return ""
    return unidecode(str(s)).lower().strip()

def fix_invalid_columns(sql_query: str, all_dfs: dict) -> str:
    """Corrige colunas inexistentes com base nas colunas reais dos DataFrames."""
    all_columns = {}
    for table, df in all_dfs.items():
        for col in df.columns:
            all_columns[col] = table

    words = sql_query.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
    for word in words:
        if '.' in word:
            parts = word.split('.', 1)
            table, col = parts[0], parts[1]
            if table in all_dfs and col not in all_dfs[table].columns:
                match = difflib.get_close_matches(col, all_dfs[table].columns, n=1)
                if match:
                    sql_query = sql_query.replace(col, match[0])
        else:
            if word in all_columns:
                sql_query = sql_query.replace(word, f"{all_columns[word]}.{word}")
    return sql_query

# ==============================================================================
# PARTE 2: CONSTRUÇÃO DO CONTEXTO (ESQUEMA + AMOSTRAS)
# ==============================================================================

def generate_full_schema_with_samples(all_dfs: dict) -> str:
    """
    Cria a representação textual do esquema e 3 exemplos de linhas por tabela.
    """
    # 1. Construção da seção de ESQUEMA
    schema_section = "========================\nESQUEMA (SQLite)\n========================\n\n"
    for table_name, df in all_dfs.items():
        schema_section += f"Tabela: {table_name}\n"
        for col in df.columns:
            suffix = " (PK/FK)" if col.lower().endswith('_id') or col.lower() == 'id' else ""
            schema_section += f"- {col}{suffix}\n"
        schema_section += "\n"

    # 2. Construção da seção de EXEMPLOS DE DADOS
    samples_section = "========================\nEXEMPLOS DE DADOS (3 linhas por tabela)\n========================\n\n"
    for table_name, df in all_dfs.items():
        samples_section += f"{table_name} (exemplos)\n"
        # Pega as 3 primeiras linhas e formata como dicionários
        top_3 = df.head(3).to_dict(orient='records')
        for i, row in enumerate(top_3, 1):
            # repr(v) garante que strings fiquem entre aspas e números fiquem puros
            row_str = ", ".join([f"{k}={repr(v)}" for k, v in row.items()])
            samples_section += f"{i}) ({row_str})\n"
        samples_section += "\n"

    return schema_section + samples_section

# ==============================================================================
# PARTE 3: GERAÇÃO DE SQL (TEXT-TO-SQL)
# ==============================================================================

def generate_sql_query_from_total(question: str, all_dfs: dict) -> str:
    """
    Gera a query SQL utilizando o esquema completo e exemplos formatados.
    """
    # 1. Obtém a representação das tabelas e dados
    full_schema_context = generate_full_schema_with_samples(all_dfs)

    # 2. Relações fixas entre as tabelas de mercado imobiliário
    relations = (
        "========================\nRELAÇÕES ENTRE TABELAS\n========================\n"
        "- buildings.id_predio = typologies.id_predio\n"
        "- buildings.id_predio = units.id_predio\n"
        "- typologies.id_tipologia = units.id_tipologia\n"
        "- units.id_unidade = units_updates.id_unidade\n\n"
    )

    # 3. Few-shot examples para orientar o modelo
    guidance_examples = """
### EXEMPLOS DE REFERÊNCIA ###
Pergunta: Quantos edifícios estão localizados na cidade de porto alegre?
SQL: SELECT COUNT(*) FROM buildings WHERE cidade_endereço = 'porto alegre';

Pergunta: Qual a área média das unidades no bairro jardim europa?
SQL: SELECT AVG(units.area_privativa)
FROM units
JOIN buildings ON units.id_predio = buildings.id_predio
WHERE buildings.bairro_endereço = 'jardim europa';
"""

    # 4. Montagem do prompt final
    system_message = config.SQL_GENERATION_SYSTEM_PROMPT
    user_message = (
        f"{guidance_examples}\n\n"
        f"{full_schema_context}"
        f"{relations}"
        "========================\n"
        "PERGUNTA DO USUÁRIO\n"
        "========================\n"
        f"{question}\n\n"
        "### INSTRUÇÃO ###\n"
        "Gere apenas o SQL puro para responder a pergunta acima, seguindo as regras do sistema."
    )

    # Debug: imprime o prompt no terminal
    print("-" * 30 + " PROMPT ENVIADO " + "-" * 30)
    print(user_message)
    print("-" * 76)

    try:
        # Chamada ao modelo local (Mistral-7B via local_llm.py)
        sql_query = generate_local_response(system_message, user_message, config.CHAT_MODEL)
        
        # Limpeza de markdown e prefixos indesejados
        sql_query = sql_query.strip()
        if sql_query.startswith('```'):
            sql_query = sql_query.lstrip('` \n').replace('sql', '', 1).strip()
        if sql_query.endswith('```'):
            sql_query = sql_query.rstrip('` \n')
        
        # Correção automática de colunas
        sql_query = fix_invalid_columns(sql_query, all_dfs)
        
        return sql_query.strip()

    except Exception as e:
        return f"-- Erro ao gerar SQL: {e}"

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