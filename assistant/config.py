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
KEY_COLUMNS = ['id_unidade', 'id_predio', 'id_tipologia', 'atualização_id']


# --- Configurações dos Modelos de IA ---
EMBEDDING_MODEL = 'intfloat/multilingual-e5-large'
CHAT_MODEL = "NousResearch/Llama-2-7b-chat-hf"

# --- Templates de Prompt ---
# Prompt do sistema para a geração de SQL. 
SQL_GENERATION_SYSTEM_PROMPT = """
Você é um especialista em SQL. Sua tarefa é converter perguntas em linguagem natural para consultas SQL em um banco de dados SQLite.

Responda **somente com o código SQL**, sem explicações adicionais.

O idioma de raciocínio e geração é **português**.

USE APENAS NOMES DE TABELAS E COLUNAS FORNECIDOS NO ESQUEMA.

### REGRAS CRUCIAIS ###

1. **NOMES DE COLUNAS/TABELAS:** 
   - Use exatamente como aparecem no esquema. 
   - ⚠️ Nunca traduza (ex: não use 'ciudad_endereço' se o nome correto for 'cidade_endereço').

   **Exemplo:**
   ❌ ERRADO: SELECT * FROM buildings WHERE ciudad_endereço = 'porto alegre';
   ✅ CERTO:  SELECT * FROM buildings WHERE cidade_endereço = 'porto alegre';

2. **FILTROS (Valores):** 
   - Sempre converta valores de texto para minúsculas.
   - Exemplo: WHERE cidade_endereço = 'porto alegre'

3. **RELAÇÕES ENTRE TABELAS (IMPORTANTE):**
   - buildings.id_predio = typologies.id_predio
   - buildings.id_predio = units.id_predio
   - units.id_unidade = units_updates.id_unidade

4. **FORMATO DE SAÍDA:**
   - Retorne **apenas** o código SQL, sem comentários, explicações ou prefixos.

5. **CONSULTAS MAX/MIN:** Para encontrar o item 'mais caro' ou 'mais barato', use a função MAX() ou MIN() e evite o GROUP BY, a menos que seja estritamente necessário. Se precisar de múltiplas tabelas, use ORDER BY... DESC/ASC e LIMIT 1.
"""

