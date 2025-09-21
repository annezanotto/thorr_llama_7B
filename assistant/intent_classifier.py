# assistant/intent_classifier.py
import json
from . import config 
from .local_llm import generate_local_response 
from . import config

def classify_intent(question: str) -> str:
    # A lógica do prompt permanece a mesma
    system_message = """    Você é um especialista em classificar a intenção do usuário para um assistente de dados imobiliários.
    Analise a pergunta do usuário e determine se ela pode ser respondida por uma consulta a um banco de dados (SQL_QUERY) ou se é uma conversa geral (GENERAL_CONVERSATION).

    - SQL_QUERY: Perguntas sobre quantidades, listas, médias, valores, contagens, rankings ou detalhes específicos de dados que estão no banco (unidades, prédios, preços, características).
    Exemplos: 'Qual a unidade mais cara?', 'Liste os prédios da Melnick Even', 'Quantos imóveis temos em Porto Alegre?'

    - DATA_ASSISTANCE: Perguntas sobre o esquema do banco de dados, as tabelas, as colunas e os relacionamentos.
    Exemplos: 'Quais dados você tem sobre os prédios?', 'O que significa a coluna 'unidade_id'?', 'Quais tabelas estão relacionadas?'

    - GENERAL_CONVERSATION: Saudações, perguntas sobre suas capacidades, perguntas de conhecimento geral que não estão nos dados, ou opiniões subjetivas.
    Exemplos: 'Olá, tudo bem?', 'O que você faz?', 'Qual a cotação do dólar hoje?', 'O mercado imobiliário está bom para investir?'
...

    Responda APENAS com um objeto JSON contendo a chave "intent" e o valor da intenção classificada.
    Exemplo de resposta válida: {"intent": "SQL_QUERY"}"""

    user_message = f"Analise a seguinte pergunta do usuário: \"{question}\""

    try:
        response_text = generate_local_response(system_message, user_message, config.CHAT_MODEL)
        
        # O modelo local precisa ser instruído a gerar um JSON válido
        response_json = json.loads(response_text)
        intent = response_json.get("intent", "UNKNOWN")
        
        print(f"DEBUG - Intenção classificada: {intent}")
        return intent
    except Exception as e:
        print(f"❌ Erro ao classificar intenção: {e}")
        return "UNKNOWN"