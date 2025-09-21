# assistant/executa_sql.py
import sqlite3
import pandas as pd
from . import config

def execute_query(sql_query: str):
    """Executa uma query SQL no banco de dados e retorna o resultado como DataFrame."""
    try:
        conn = sqlite3.connect(config.DB_FILE)
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        # Retorna a mensagem de erro como uma string para ser impressa no console
        return f"Erro ao executar a query: {e}"


def get_all_tables_dfs():
    """
    Carrega todas as tabelas do banco de dados para um dicionário de DataFrames.
    Essencial para o setup inicial do FAISS no main.py.
    """
    try:
        conn = sqlite3.connect(config.DB_FILE)
        # Pega o nome de todas as tabelas no banco de dados
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        dfs = {}
        # Para cada tabela encontrada, carrega-a para um DataFrame
        for table_name in tables:
            name = table_name[0]
            dfs[name] = pd.read_sql_query(f"SELECT * FROM {name}", conn)
        
        conn.close()
        print(f"Carregadas {len(dfs)} tabelas do banco de dados: {list(dfs.keys())}")
        return dfs
    except Exception as e:
        print(f"❌ ERRO FATAL: Não foi possível carregar as tabelas do banco de dados '{config.DB_FILE}'.")
        print(f"   Verifique se o arquivo existe e se o script 'setup_database.py' foi executado.")
        print(f"   Detalhe do erro: {e}")
        # Retorna um dicionário vazio ou sai do programa se for um erro crítico
        return {}