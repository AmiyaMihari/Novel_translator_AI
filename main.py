import streamlit as st
import os
import tempfile
import sys

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
        
    else:
        st.sidebar.warning("No se encontraron modelos. Descarga uno con 'ollama pull <modelo>'")
        selected_model = None
else:
    st.sidebar.error(msg)
    selected_model = None

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
            
            translated_chunks = []
            dict_context = get_dictionary_context(source_lang, target_lang)
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"Traduciendo bloque {i+1} de {len(chunks)}...")
                
                # Show current chunk
                with st.expander(f"Bloque {i+1} (Original)", expanded=False):
                    st.text(chunk)
                
                if selected_model:
                    translated_text = translate_chunk(chunk, source_lang, target_lang, dict_context, model_name=selected_model)
                else:
                    translated_text = "Error: No hay modelo seleccionado."
                    
                translated_chunks.append(translated_text)
                
                with st.expander(f"Bloque {i+1} (Traducción)", expanded=True):
                    st.write(translated_text)
                
                # Update progress
                progress = (i + 1) / len(chunks)
                progress_bar.progress(progress)
                
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
