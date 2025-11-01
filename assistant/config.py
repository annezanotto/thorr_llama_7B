# thorr_assistant/config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()
# --- Configurações do Banco de Dados ---
DB_FILE = "database.db"

# --- Configurações de Arquivos e Pastas ---
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
KEY_COLUMNS = ['id_unidade', 'id_predio', 'id_tipologia', 'atualização_id']


# --- Configurações dos Modelos de IA ---
EMBEDDING_MODEL = 'intfloat/multilingual-e5-large'
CHAT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

# --- Templates de Prompt ---
# Prompt do sistema para a geração de SQL. 
SQL_GENERATION_SYSTEM_PROMPT = """Você é um especialista em SQL para SQLite. Sua tarefa é converter a pergunta do usuário para uma consulta SQL.
Seja preciso e conciso.

USE APENAS NOMES DE TABELAS E COLUNAS DO ESQUEMA.
***REGRAS CRUCIAIS:***
1.  **SAÍDA ÚNICA:** Gere **APENAS UMA** consulta SQL. Nunca inclua comentários, explicações ou múltiplos comandos.
2.  **NOMES:** Use nomes de tabelas e colunas EXATAMENTE como aparecem no esquema (Ex: use 'cidade_endereço', não 'ciudad_endereço').
3.  **FILTROS:** Ao filtrar valores (strings como nomes), SEMPRE use minúsculas (Ex: 'porto alegre').
4.  **LÓGICA JOIN:** Se a coluna de filtro (ex: 'bairro_endereço') estiver em outra tabela, VOCÊ DEVE usar JOIN (Ex: JOIN buildings ON units.id_predio = buildings.id_predio)."""

