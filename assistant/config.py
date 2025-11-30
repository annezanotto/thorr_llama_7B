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
SQL_GENERATION_SYSTEM_PROMPT =  """
Você é um especialista em SQL para SQLite. Sua tarefa é converter a pergunta do usuário em uma ÚNICA consulta SQL válida.

Siga rigorosamente as regras:

1. Gere apenas UMA consulta SQL, sem explicações ou comentários.
2. Use os nomes das tabelas e colunas EXATAMENTE como aparecem no esquema fornecido.
3. Nunca traduza ou modificar nomes de colunas (ex: use 'cidade_endereço', nunca 'ciudad_endereço').
4. Sempre prefixe as colunas com o nome da tabela (ex: buildings.cidade_endereço).
5. Strings usadas em filtros (como nomes de cidades, bairros, incorporadoras) devem ser convertidas para minúsculas.
6. Utilize JOINs quando a informação filtrada estiver em outra tabela.
7. Para cálculos de área, use:
   - units.area_privativa (área da unidade)
   - typologies.area_privada (área da tipologia)
8. Gere apenas SQL compatível com SQLite.
9. A consulta SQL NÃO deve conter ponto e vírgula no final (NUNCA inclua ‘;’).
"""

