# assistant/local_llm.py
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Dicionário para armazenar o modelo e o tokenizer após o carregamento inicial
_model_cache = {}

def get_local_llm_pipeline(model_name: str):
    if model_name not in _model_cache:
        print(f"Carregando modelo local: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        _model_cache[model_name] = {"tokenizer": tokenizer, "model": model}
    
    return _model_cache[model_name]["tokenizer"], _model_cache[model_name]["model"]

def generate_local_response(system_prompt: str, user_prompt: str, model_name: str) -> str:
    tokenizer, model = get_local_llm_pipeline(model_name)
    
    # Formata o prompt para o modelo de acordo com o chat template
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # Gera a resposta
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7)
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove o prompt original da resposta
    return response.replace(input_text, "").strip()