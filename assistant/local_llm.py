# assistant/local_llm.py
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

# Dicionário para armazenar o modelo e o tokenizer após o carregamento inicial
_model_cache = {}

def get_local_llm_pipeline(model_name: str):
    if model_name not in _model_cache:
        print(f"Carregando modelo local: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            quantization_config=bnb_config, # <-- Use a nova config
            device_map="auto"
        )
        
        _model_cache[model_name] = {"tokenizer": tokenizer, "model": model}
    
    return _model_cache[model_name]["tokenizer"], _model_cache[model_name]["model"]

def generate_local_response(system_prompt: str, user_prompt: str, model_name: str) -> str:
    tokenizer, model = get_local_llm_pipeline(model_name)
    
    # 1. Formato da mensagem de Sistema (System Prompt)
    system_message_formatted = f"<<SYS>>\n{system_prompt}\n<</SYS>>\n\n"
    
    # 2. Formato final do Prompt
    # O Llama 2 usa a estrutura [INST] para instruções e /s para início/fim de diálogo.
    input_text = f"<s>[INST] {system_message_formatted}{user_prompt} [/INST]"
        
    # Gera a resposta
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7)
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove o prompt original da resposta
    response_start_tag = "[/INST]"
    if response_start_tag in response:
        response = response.split(response_start_tag, 1)[1].strip()
        
    return response.strip()