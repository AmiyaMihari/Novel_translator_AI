import os
from fpdf import FPDF
from ebooklib import epub

def export_to_pdf(text_chunks, filename, title="Translated Novel"):
    """
    Exports a list of text chunks to a PDF file.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # We use a built-in font. For unicode support (like Japanese/Chinese),
    # an external unicode font (.ttf) must be added. For English/Spanish it's fine.
    # To keep it simple, we just use the default latin-1, but replace incompatible chars or use a trick.
    # Note: For full CJK support, a true type font is strictly required. 
    # For now we encode/decode to ignore unmappable characters or replace them,
    # as setting up CJK fonts requires external font files.
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    for chunk in text_chunks:
        # Encode with replace to avoid fpdf latin-1 errors on weird characters
        clean_chunk = chunk.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, clean_chunk)
        pdf.ln(5)
        
    pdf.output(filename)
    return filename

def export_to_epub(text_chunks, filename, title="Translated Novel"):
    """
    Exports a list of text chunks to an EPUB file.
    """
    book = epub.EpubBook()
    book.set_identifier(title.lower().replace(' ', '_'))
    book.set_title(title)
    book.set_language('es') # Defaulting to ES
    
    chapters = []
    spine = ['nav']
    
    for i, chunk in enumerate(text_chunks):
        chapter = epub.EpubHtml(title=f'Chapter {i+1}', file_name=f'chap_{i+1}.xhtml', lang='es')
        # Simple HTML formatting
        html_content = f"<h1>Capítulo {i+1}</h1>"
        for paragraph in chunk.split('\n'):
            if paragraph.strip():
                html_content += f"<p>{paragraph}</p>"
        
        chapter.content = html_content
        book.add_item(chapter)
        chapters.append(chapter)
        spine.append(chapter)
        
    # Create TOC
    book.toc = tuple(chapters)
    
    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Define CSS style
    style = 'BODY {color: white;}'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)
    
    book.spine = spine
    epub.write_epub(filename, book, {})
    return filename
