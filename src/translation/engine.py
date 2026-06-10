import ollama
import re

def translate_chunk(text, source_lang, target_lang, dictionary_context="", model_name='gemma4:26b', disable_thinking=True):
    """
    Translates a chunk of text using the selected local Ollama model.
    """
    
    combined_prompt = f"""You are a professional novel translator.
Translate the following text from {source_lang} to {target_lang}.
Maintain the original tone, style, and formatting (e.g. newlines, paragraphs) as much as possible.
Do not add any additional comments, notes, or explanations. Only output the translated text.

{dictionary_context}

TEXT TO TRANSLATE:
{text}
"""

    options = {'num_ctx': 4096, 'num_predict': 2048}

    try:
        # First attempt: Try using the top-level 'think' parameter if disable_thinking is True
        kwargs = {
            'model': model_name,
            'messages': [{'role': 'user', 'content': combined_prompt}],
            'options': options,
            'keep_alive': '15m'
        }
        
        if disable_thinking:
            # En Ollama, el parámetro 'think' va en el nivel principal, NO dentro de options
            kwargs['think'] = False

        try:
            response = ollama.chat(**kwargs)
        except Exception as e:
            # If the specific model or older ollama version rejects the 'think' parameter, fallback without it
            if 'think' in kwargs:
                del kwargs['think']
                response = ollama.chat(**kwargs)
            else:
                raise e
        
        output = response['message']['content']
        # Strip <think> tags if a reasoning model like deepseek-r1 was used
        output = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL).strip()
        
        if not output:
            # If output is completely empty, return the raw dictionary for debugging
            return f"⚠️ ERROR: El modelo devolvió una cadena vacía. Respuesta raw de Ollama: {response}"
        
        return output
    except Exception as e:
        return f"Error during translation: {str(e)}"

def test_connection():
    """
    Tests if the Ollama connection is available and returns the list of available models.
    """
    try:
        models_response = ollama.list()
        
        # Depending on the ollama python client version, it might be a dict or an object
        if hasattr(models_response, 'models'):
            model_list = models_response.models
        else:
            model_list = models_response.get('models', [])
            
        model_names = []
        for m in model_list:
            if hasattr(m, 'model'):
                model_names.append(m.model)
            elif isinstance(m, dict) and 'name' in m:
                model_names.append(m['name'])
            elif isinstance(m, dict) and 'model' in m:
                model_names.append(m['model'])
        
        if model_names:
            return True, "Ollama is running.", model_names
        else:
            return False, "Ollama is running but no models are downloaded.", []
    except Exception as e:
        return False, f"Ollama connection failed. Is it running? Error: {str(e)}", []
