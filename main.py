# main.py
from sentence_transformers import SentenceTransformer
from assistant import config, executa_sql, pipeline, intent_classifier, conversation
from assistant.pipeline import run_sql_pipeline


def main():
    # --- Etapa de Configuração Inicial ---
    print("Iniciando o assistente de dados Thorr...")
    print("Carregando dados e modelo de embeddings...")

    # Carrega DataFrames do novo banco de dados
    dfs = executa_sql.get_all_tables_dfs()
    base_texts = config.BASE_TEXTS  # Textos descritivos das tabelas e colunas

    model = SentenceTransformer(config.EMBEDDING_MODEL)
    index, table_names, _, _ = pipeline.setup_faiss_and_model(dfs, base_texts, model)
    
    print("Assistente pronto! Digite 'sair' para encerrar.")
    print("-" * 50)


    while True:
        question = input("> Digite sua pergunta: ").strip()
        if question.lower() in ['sair', 'exit', 'quit']:
            print("Até logo!")
            break

        intent = intent_classifier.classify_intent(question)

        if intent == 'SQL_QUERY':

            sql_query = run_sql_pipeline(
                question=question,
                model=model,
                index=index,
                table_names=table_names,
                all_dfs=dfs,
                verbose=True  # Mude para False para desligar o debug!
            )
            
            print("\n[Resultado Final]:")
            result = executa_sql.execute_query(sql_query)
            print(result)
            
        elif intent == 'DATA_ASSISTANCE':
            answer = pipeline.handle_data_assistance(question, dfs)
            print(f"\nThorr: {answer}")

        elif intent == 'GENERAL_CONVERSATION':
            answer = conversation.handle_general_conversation(question)
            print(f"\nThorr: {answer}")
        else:
            print("\nThorr: Desculpe, não consegui entender. Poderia reformular?")
        
        print("-" * 50)

if __name__ == "__main__":
    main()