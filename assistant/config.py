# thorr_assistant/config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()
# --- Configurações do Banco de Dados ---
DB_FILE = "financiamento.db"

# --- Configurações de Arquivos e Pastas ---
# DATA_FILES = {
#     'buildings': 'tables/buildings.xlsx',
#     'typologies': 'tables/typologies.xlsx',
#     'units': 'tables/units.xlsx',
#     'units_updates': 'tables/units_updates.xlsx',
# }

# --- Descrições do Esquema do Banco de Dados ---
# Descrições base para cada tabela, usadas na criação da representação
BASE_TEXTS = {
    'Clientes': "Armazena os dados cadastrais dos clientes que contratam financiamentos.",
    'ProdutosFinanciamento': "Define os tipos de produtos financeiros oferecidos pela instituição.",
    'Contratos': "Registra os contratos de financiamento firmados entre clientes e a instituição",
    'Parcelas': "Contém o detalhamento das parcelas de cada contrato.",
    'Garantias': "Lista as garantias associadas a cada contrato de financiamento.",
    'PagamentosRealizados': "Registra os pagamentos realizados pelos clientes em relação às parcelas dos contratos."
}

# Colunas-chave que devem ser mantidas durante o refinamento para garantir os JOINs
KEY_COLUMNS = ['cliente_id', 'produto_id', 'contrato_id', 'cliente_id', 'produto_id', 'parcela_id']


# --- Configurações dos Modelos de IA ---
EMBEDDING_MODEL = 'intfloat/multilingual-e5-large'
CHAT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

# --- Templates de Prompt ---
# Prompt do sistema para a geração de SQL. 
SQL_GENERATION_SYSTEM_PROMPT =  """
Você é um especialista em SQL para SQLite. Sua tarefa é converter a pergunta do usuário em uma ÚNICA consulta SQL válida.

Siga rigorosamente as regras:

1. Gere apenas UMA consulta SQL, sem explicações ou comentários.
2. Use os nomes das tabelas e colunas EXATAMENTE como aparecem no esquema fornecido.
3. Nunca traduza ou modificar nomes de colunas.
4. Sempre prefixe as colunas com o nome da tabela (ex: Contratos.valor_total).
5. Utilize JOINs quando a informação filtrada estiver em outra tabela.
6. Gere apenas SQL compatível com SQLite.
7. A consulta SQL NÃO deve conter ponto e vírgula no final (NUNCA inclua ‘;’).
"""
