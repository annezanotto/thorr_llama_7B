# main.py
from sentence_transformers import SentenceTransformer
from assistant import config, executa_sql, pipeline, intent_classifier, conversation
from assistant.pipeline import generate_sql_query_from_total 

def main():
    # --- Etapa de Configuração Inicial ---
    print("Iniciando o assistente de dados Thorr...")
    print("Carregando dados...")

    # Carrega DataFrames do banco de dados (all_dfs)
    dfs = executa_sql.get_all_tables_dfs() 
    
    
    print("Assistente pronto! Digite 'sair' para encerrar.")
    print("-" * 50)

    while True:
        question = input("> Digite sua pergunta: ").strip()
        if question.lower() in ['sair', 'exit', 'quit']:
            print("Até logo!")
            break

        # Classifica a intenção (SQL, Ajuda ou Conversa)
        intent = intent_classifier.classify_intent(question) 

        if intent == 'SQL_QUERY':
            # Chamada para a sua nova função que usa o esquema total + 3 exemplos
            sql_query = generate_sql_query_from_total(
                question=question,
                all_dfs=dfs
            )
            
            print("\n[SQL Gerado]:")
            print(sql_query)
            
            print("\n[Resultado Final]:")
            # Executa a query gerada no banco SQLite
            result = executa_sql.execute_query(sql_query) 
            print(result)
            
        elif intent == 'DATA_ASSISTANCE':
            # Explica o esquema das tabelas
            answer = pipeline.handle_data_assistance(question, dfs) 
            print(f"\nThorr: {answer}")

        elif intent == 'GENERAL_CONVERSATION':
            # Conversa amigável com a persona Thori
            answer = conversation.handle_general_conversation(question) 
            print(f"\nThori: {answer}")
        else:
            print("\nThori: Desculpe, não consegui entender. Poderia reformular?")
        
        print("-" * 50)

if __name__ == "__main__":
    main()