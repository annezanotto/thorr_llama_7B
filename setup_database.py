# setup_database.py
import pandas as pd
import sqlite3
import os
from unidecode import unidecode  # <-- NOVO: Importa a biblioteca de normalização

# --- Constantes de Configuração ---
DB_FILE = "database.db"
DATA_DIR = "tables" 

# --- FUNÇÃO DE NORMALIZAÇÃO ---
def normalize_text_column(s):
    """
    Remove caracteres especiais, acentos e garante que o texto seja string limpa
    e em minúsculas antes de salvar no DB.
    """
    if s is None:
        return ""
    # Tenta decodificar de latin-1 ou apenas converte para string
    try:
        s = str(s).encode('latin-1').decode('utf-8')
    except:
        s = str(s)

    # Remove acentos (unidecode) e converte para minúsculas
    return unidecode(s).lower().strip()
# -----------------------------

def create_database():
    """
    Lê os arquivos Excel da pasta 'tables', trata os tipos de dados e os salva
    em um banco de dados SQLite persistente ('database.db').
    """
    # Se o banco de dados já existir, ele será removido para garantir uma recriação limpa.
    if os.path.exists(DB_FILE):
        print(f"O banco de dados '{DB_FILE}' já existe. Removendo para recriar.")
        os.remove(DB_FILE)

    # Conecta-se a um arquivo no disco
    conn = sqlite3.connect(DB_FILE)
    print(f"Conexão com o banco de dados '{DB_FILE}' estabelecida.")

    try:
        excel_files = {
            'buildings': 'buildings.xlsx',
            'typologies': 'typologies.xlsx',
            'units': 'units.xlsx',
            'units_updates': 'units_updates.xlsx',
        }

        for table_name, file_name in excel_files.items():
            file_path = os.path.join(DATA_DIR, file_name)
            print(f"Processando '{file_path}'...")
            
            df = pd.read_excel(file_path)
            
            # --- NOVO: APLICA A NORMALIZAÇÃO ANTES DO TRATAMENTO DE TIPOS ---
            for col in df.columns:
                # Aplica a limpeza apenas em colunas de texto
                if df[col].dtype == "object" or df[col].dtype == "string":
                    df[col] = df[col].apply(lambda x: normalize_text_column(x))
            # -----------------------------------------------------------------
            
            # Força conversão de colunas com números muito grandes para string
            for col in df.columns:
                # Verifica se a coluna é numérica (inteiro ou float)
                if pd.api.types.is_numeric_dtype(df[col]):
                    # Se houver valores fora do limite de um inteiro de 64 bits do SQLite
                    if (df[col].dropna().max() > 2**63 - 1) or (df[col].dropna().min() < -2**63):
                        print(f"⚠️ Coluna '{col}' na tabela '{table_name}' convertida para TEXT (valores muito grandes).")
                        df[col] = df[col].astype(str)
            
            # Força todas as colunas "object" a virarem string explícita para o SQLite
            df = df.astype({col: "string" for col in df.columns if df[col].dtype == "object"})

            # Grava o DataFrame tratado no banco de dados SQLite
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"✅ Tabela '{table_name}' criada com sucesso.")

    except FileNotFoundError as e:
        print(f"\n❌ ERRO: Arquivo não encontrado! Verifique se a pasta '{DATA_DIR}' existe e contém os arquivos Excel.")
        print(f"   Detalhe: {e}")
    except Exception as e:
        print(f"\n❌ ERRO ao processar os arquivos e salvar no banco de dados. Causa provável: problema de tipo de dado.")
        print(f"   Detalhe: {e}")
    finally:
        conn.close()
        print("\nProcesso finalizado. Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    create_database()