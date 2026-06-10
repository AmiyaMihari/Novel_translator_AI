import streamlit as st
import os
import tempfile
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the parent directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.dictionary.database import init_db, add_term, get_all_terms, delete_term, get_dictionary_context
from src.document.parser import process_document
from src.translation.engine import translate_chunk, test_connection
from src.document.exporter import export_to_pdf, export_to_epub

# Initialize the database
init_db()

st.set_page_config(page_title="AI Novel Translator", layout="wide")

st.title("📚 AI Novel Translator (Local LLM)")
st.write("Translates ePub and TXT files using a local instance of Ollama (gemma4:26b).")

# Sidebar for settings and dictionary
st.sidebar.header("⚙️ Configuración")

# Language settings
LANGUAGES = ["Inglés", "Español", "Japonés", "Chino"]
source_lang = st.sidebar.selectbox("Idioma de origen", LANGUAGES, index=2)  # Default: Japonés
target_lang = st.sidebar.selectbox("Idioma de destino", LANGUAGES, index=1)  # Default: Español

# Ollama connection test and model selection
status, msg, model_names = test_connection()
if status:
    st.sidebar.success(msg)
    if model_names:
        # Default to deepseek-r1:14b if available since gemma4:26b is too large for some GPUs
        default_index = 0
        for i, name in enumerate(model_names):
            if 'deepseek-r1:14b' in name:
                default_index = i
                break
        selected_model = st.sidebar.selectbox("Modelo de IA", model_names, index=default_index)
        
        # Toggle for thinking mode
        st.sidebar.markdown("### ⚡ Opciones del Modelo")
        disable_thinking = st.sidebar.checkbox("Desactivar razonamiento (Modo Rápido)", value=True, help="Si usas DeepSeek o Qwen, esto apaga el modo 'pensamiento' para traducir mucho más rápido.")
        
    else:
        st.sidebar.warning("No se encontraron modelos. Descarga uno con 'ollama pull <modelo>'")
        selected_model = None
        disable_thinking = True
else:
    st.sidebar.error(msg)
    selected_model = None
    disable_thinking = True

st.sidebar.markdown("---")
st.sidebar.header("⚡ Rendimiento")
num_workers = st.sidebar.slider("Traducciones en paralelo", 1, 8, 4, help="Número de bloques a traducir simultáneamente. Debe coincidir con la variable OLLAMA_NUM_PARALLEL de tu servidor Ollama.")
st.sidebar.info("💡 Nota: Para que el paralelismo sea efectivo, asegúrate de iniciar Ollama con OLLAMA_NUM_PARALLEL ajustado. (Ej. `OLLAMA_NUM_PARALLEL=4 ollama serve`)")

st.sidebar.markdown("---")
st.sidebar.header("📖 Diccionario / Memoria")
st.sidebar.write("Agrega términos para mantener la consistencia (nombres, lugares, etc).")

with st.sidebar.form("add_term_form"):
    orig = st.text_input("Término original")
    trans = st.text_input("Traducción")
    term_type = st.selectbox("Tipo", ["Personaje", "Lugar", "Objeto", "Otro"])
    notes = st.text_area("Notas (Opcional)")
    submitted = st.form_submit_button("Agregar término")
    
    if submitted:
        if orig and trans:
            add_term(orig, trans, term_type, source_lang, target_lang, notes)
            st.success("Término agregado!")
        else:
            st.error("Los campos Original y Traducción son obligatorios.")

# Display current dictionary terms
st.sidebar.subheader("Términos guardados")
terms = get_all_terms(source_lang, target_lang)
if terms:
    for t in terms:
        col1, col2 = st.sidebar.columns([4, 1])
        col1.write(f"**{t['original_term']}** -> {t['translated_term']} ({t['term_type']})")
        if col2.button("❌", key=f"del_{t['id']}"):
            delete_term(t['id'])
            st.rerun()
else:
    st.sidebar.write("No hay términos guardados para esta combinación de idiomas.")


# Main Content Area
st.header("📄 Subir Libro")
uploaded_file = st.file_uploader("Sube tu archivo .epub o .txt", type=['epub', 'txt'])

if uploaded_file is not None:
    # Save the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
        
    st.info(f"Procesando el archivo: {uploaded_file.name}")
    
    # Process document
    try:
        chunks = process_document(tmp_file_path)
        st.success(f"Documento dividido en {len(chunks)} bloques de texto.")
        
        # Export format selection
        export_format = st.radio("Formato de exportación:", ["TXT", "PDF", "EPUB"], horizontal=True)
        
        if st.button("🚀 Iniciar Traducción"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            translated_chunks = [None] * len(chunks)
            dict_context = get_dictionary_context(source_lang, target_lang)
            
            def worker(index, chunk_text):
                try:
                    if selected_model:
                        res = translate_chunk(chunk_text, source_lang, target_lang, dict_context, model_name=selected_model, disable_thinking=disable_thinking)
                        return index, res
                    else:
                        return index, "Error: No hay modelo seleccionado."
                except Exception as e:
                    return index, f"Error en bloque {index+1}: {str(e)}"
                    
            start_time = time.time()
            completed = 0
            
            status_text.text(f"Iniciando traducción en paralelo ({num_workers} hilos)...")
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = {executor.submit(worker, i, chunk): i for i, chunk in enumerate(chunks)}
                
                for future in as_completed(futures):
                    idx, result = future.result()
                    translated_chunks[idx] = result
                    completed += 1
                    
                    elapsed = time.time() - start_time
                    eta = (elapsed / completed) * (len(chunks) - completed) if completed > 0 else 0
                    progress_bar.progress(completed / len(chunks))
                    status_text.text(f"Traduciendo... {completed}/{len(chunks)} completados. ETA: {int(eta)}s")
            
            status_text.text("✅ Traducción completada! Renderizando vista previa...")
            
            # Mostrar resultados en orden tras finalizar los hilos
            for i, (orig, trans) in enumerate(zip(chunks, translated_chunks)):
                with st.expander(f"Bloque {i+1} (Original)", expanded=False):
                    st.text(orig)
                with st.expander(f"Bloque {i+1} (Traducción)", expanded=True):
                    st.write(trans)
            
            status_text.text("✅ Traducción completada! Preparando archivo...")
            
            # Combine translation and offer download
            final_title = f"Translated_{uploaded_file.name.split('.')[0]}"
            
            if export_format == "TXT":
                final_text = "\n\n".join(translated_chunks)
                st.download_button(
                    label="📥 Descargar Traducción (TXT)",
                    data=final_text,
                    file_name=f"{final_title}.txt",
                    mime="text/plain"
                )
            elif export_format == "PDF":
                pdf_path = export_to_pdf(translated_chunks, f"/tmp/{final_title}.pdf", title=final_title)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Traducción (PDF)",
                        data=f,
                        file_name=f"{final_title}.pdf",
                        mime="application/pdf"
                    )
            elif export_format == "EPUB":
                epub_path = export_to_epub(translated_chunks, f"/tmp/{final_title}.epub", title=final_title)
                with open(epub_path, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Traducción (EPUB)",
                        data=f,
                        file_name=f"{final_title}.epub",
                        mime="application/epub+zip"
                    )
            
    except Exception as e:
        st.error(f"Error procesando el documento: {str(e)}")
        
    finally:
        # Cleanup
        os.unlink(tmp_file_path)
