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
    Gera a query SQL consolidando regras rígidas, esquema e exemplos.
    """
    # 1. Recupera o Esquema e Amostras (3 linhas por tabela)
    full_schema_context = generate_full_schema_with_samples(all_dfs)

    # 2. Define as Relações de Join
    relations = (
        "========================\nRELAÇÕES (CHAVES PARA JOIN)\n========================\n"
        "- buildings.id_predio = typologies.id_predio\n"
        "- buildings.id_predio = units.id_predio\n"
        "- typologies.id_tipologia = units.id_tipologia\n"
        "- units.id_unidade = units_updates.id_unidade\n\n"
    )

    # 3. Regras do Config (Suas 9 regras cruciais)
    system_rules = config.SQL_GENERATION_SYSTEM_PROMPT

    # 4. Montagem do prompt com "Guardrails" (Proteções)
    # Colocamos a Pergunta e a Instrução de "SQL POURO" no final para evitar alucinações
    user_message = (
        f"{full_schema_context}\n"
        f"{relations}\n"
        "========================\n"
        "REGRAS OBRIGATÓRIAS\n"
        "========================\n"
        f"{system_rules}\n\n"
        "### EXEMPLO DE ESTILO ###\n"
        "Pergunta: bairros com mais de 5 andares\n"
        "SQL: SELECT DISTINCT buildings.bairro_endereço FROM buildings WHERE buildings.numero_andares > 5\n\n"
        "========================\n"
        "PERGUNTA DO USUÁRIO\n"
        "========================\n"
        f"{question}\n\n"
        "Gere o SQL seguindo as regras (sem ';' e com prefixos):"
    )

    print("-" * 30 + " PROMPT ENVIADO " + "-" * 30)
    print(user_message)

    try:
        # Passamos o system_rules como instrução de sistema no modelo
        sql_query = generate_local_response(system_rules, user_message, config.CHAT_MODEL)
        
        # Limpeza agressiva de Markdown e quebras de linha
        sql_query = sql_query.strip().replace('```sql', '').replace('```', '').split(';')[0].strip()
        
        # Garante que não haja ponto e vírgula (Regra 9)
        sql_query = sql_query.replace(';', '')

        # Correção final de colunas
        sql_query = fix_invalid_columns(sql_query, all_dfs)
        
        return sql_query

    except Exception as e:
        return f"-- Erro na geração: {e}"

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