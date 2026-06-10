import ollama

def translate_chunk(text, source_lang, target_lang, dictionary_context="", model_name='gemma4:26b', num_gpu=None, num_ctx=None):
    """
    Translates a chunk of text using the selected local Ollama model.
    """
    
    system_prompt = f"""You are a professional novel translator.
Translate the following text from {source_lang} to {target_lang}.
Maintain the original tone, style, and formatting (e.g. newlines, paragraphs) as much as possible.
Do not add any additional comments, notes, or explanations. Only output the translated text.

{dictionary_context}
"""

    options = {}
    if num_gpu is not None:
        options['num_gpu'] = num_gpu
    if num_ctx is not None:
        options['num_ctx'] = num_ctx

    try:
        response = ollama.chat(model=model_name, messages=[
            {
                'role': 'system',
                'content': system_prompt
            },
            {
                'role': 'user',
                'content': text
            }
        ], options=options)
        return response['message']['content']
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
