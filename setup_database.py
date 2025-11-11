# setup_database.py
import pandas as pd
import sqlite3
import os
from unidecode import unidecode 

# --- Constantes de Configuração ---
DB_FILE = "database.db"
DATA_DIR = "tables" 
CLEANED_DATA_DIR = "tables_cleaned" # <-- NOVO: Pasta para salvar os arquivos Excel limpos

# --- FUNÇÃO DE NORMALIZAÇÃO DE CARACTERES (MANTIDA) ---
def normalize_text_column(s):
    # ... (código da função mantido) ...
    if s is None:
        return ""
    try:
        s = str(s).encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
    except:
        s = str(s)
    return unidecode(s).lower().strip()
# -----------------------------

# --- FUNÇÃO DE LIMPEZA DE QUALIDADE DE DADOS (MANTIDA) ---
def clean_dataframe(df, table_name):
    # ... (código da função clean_dataframe mantido - omisso aqui por brevidade) ...
    
    # --- 1. FILTROS DE OUTLIER E NULOS CRÍTICOS ---
    if table_name == 'typologies':
        df = df.dropna(subset=['area_privada', 'quartos'])
        if df['area_privada'].count() > 10:
            area_limit = df['area_privada'].quantile(0.999)
            df = df[df['area_privada'] <= area_limit]

    if table_name == 'units':
        df = df.dropna(subset=['area_privativa'])
        if 'andar' in df.columns:
            df = df[df['andar'] <= 100]
        if df['area_privativa'].count() > 10:
            area_limit = df['area_privativa'].quantile(0.999)
            df = df[df['area_privativa'] <= area_limit]
    
    # --- 2. REMOÇÃO DE RUÍDO ---
    if table_name == 'typologies':
        df = df.drop(columns=['area_exterior', 'infraestrutura', 'area_total'], errors='ignore')
    if table_name == 'units':
        df = df.drop(columns=['area_externa'], errors='ignore')
    if table_name == 'buildings':
        df = df.drop(columns=['segmento'], errors='ignore')
        
    return df
# -----------------------------

def create_database():
    """
    Lê os arquivos Excel da pasta 'tables', trata os tipos de dados e os salva
    em um banco de dados SQLite persistente ('database.db').
    """
    if os.path.exists(DB_FILE):
        print(f"O banco de dados '{DB_FILE}' já existe. Removendo para recriar.")
        os.remove(DB_FILE)

    # Cria a pasta para os arquivos limpos, se não existir
    os.makedirs(CLEANED_DATA_DIR, exist_ok=True) # <-- NOVO
    print(f"Pasta de dados limpos criada em: '{CLEANED_DATA_DIR}'") # <-- NOVO

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
            
            # 1. APLICA A NORMALIZAÇÃO DE CARACTERES
            for col in df.columns:
                if df[col].dtype == "object" or df[col].dtype == "string":
                    df[col] = df[col].apply(lambda x: normalize_text_column(x))

            # 2. APLICA A LIMPEZA DE QUALIDADE DE DADOS (Outliers e Nulos)
            df = clean_dataframe(df, table_name)
            
            # --- NOVO: SALVA O ARQUIVO EXCEL LIMPO ---
            cleaned_file_path = os.path.join(CLEANED_DATA_DIR, f"{table_name}_cleaned.xlsx")
            df.to_excel(cleaned_file_path, index=False)
            print(f"✅ Arquivo limpo salvo em: '{cleaned_file_path}'")
            # --- FIM NOVO ---
            
            # 3. Força conversão de colunas com números muito grandes para string
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    if (df[col].dropna().max() > 2**63 - 1) or (df[col].dropna().min() < -2**63):
                        print(f"⚠️ Coluna '{col}' na tabela '{table_name}' convertida para TEXT (valores muito grandes).")
                        df[col] = df[col].astype(str)
            
            # 4. Força todas as colunas "object" a virarem string explícita para o SQLite
            df = df.astype({col: "string" for col in df.columns if df[col].dtype == "object"})

            # Grava o DataFrame tratado no banco de dados SQLite
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"✅ Tabela '{table_name}' criada com sucesso no SQLite.")

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