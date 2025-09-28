# thorr_assistant/config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# --- Chaves de API e Segurança ---
DB_FILE = "database.db"

# --- Configurações de Arquivos e Pastas ---
# Dicionário com os nomes das tabelas e seus respectivos arquivos
DATA_FILES = {
    'buildings': 'tables/buildings.xlsx',
    'typologies': 'tables/typologies.xlsx',
    'units': 'tables/units.xlsx',
    'units_updates': 'tables/units_updates.xlsx',
}

# --- Descrições do Esquema do Banco de Dados ---
# Descrições base para cada tabela, usadas na criação da representação
BASE_TEXTS = {
    'buildings': "Edifícios com dados de incorporadora/construtora, endereço, cidade, estado, status.",
    'typologies': "Tipologias: configuração de quartos, banheiros, suites, lavabos e área, por id_predio.",
    'units': "Unidades individuais para venda/aluguel: andar, área, número, id_predio e tipologia.",
    'units_updates': "Histórico de preços das unidades: disponibilidade, preço, descontos, datas.",
}

# Colunas-chave que devem ser mantidas durante o refinamento para garantir os JOINs
KEY_COLUMNS = ['id_unidade', 'id_predio', 'id_tipologia', 'unidade_id', 'id_atualização']


# --- Configurações dos Modelos de IA ---
EMBEDDING_MODEL = 'intfloat/multilingual-e5-large'
CHAT_MODEL = "NousResearch/Llama-2-7b-chat-hf"

# --- Templates de Prompt ---
# Prompt do sistema para a geração de SQL. Mantê-lo aqui limpa o código principal.
SQL_GENERATION_SYSTEM_PROMPT = """Você é um especialista em SQL. Sua tarefa é converter perguntas em linguagem natural para consultas SQL para um banco de dados SQLite. 
Responda apenas com o código SQL, sem explicações adicionais, e não use markdown (```sql). 
Use as tabelas e colunas fornecidas no esquema. As junções (JOIN) devem ser feitas usando as colunas de ID que conectam as tabelas, como 'id_predio' ou 'unidade_id'. 
Certifique-se de que os nomes das tabelas e colunas na consulta correspondam exatamente aos do esquema."""