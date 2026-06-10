import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def parse_epub(file_path):
    """
    Parses an epub file and returns a list of text strings, 
    one for each chapter/document in the epub.
    """
    book = epub.read_epub(file_path)
    chapters_text = []
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Parse HTML and extract text
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator='\n')
            # Clean up excessive newlines
            clean_text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
            if clean_text:
                chapters_text.append(clean_text)
                
    return chapters_text

def chunk_text(text, target_words=1000):
    """
    Splits text into chunks of approximately `target_words` words,
    trying to split at paragraph or sentence boundaries.
    """
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for paragraph in paragraphs:
        word_count = len(paragraph.split())
        
        if current_word_count + word_count > target_words and current_chunk:
            # Save current chunk and start a new one
            chunks.append('\n'.join(current_chunk))
            current_chunk = [paragraph]
            current_word_count = word_count
        else:
            current_chunk.append(paragraph)
            current_word_count += word_count
            
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
        
    return chunks

def process_document(file_path):
    """
    Reads a document (epub or txt) and returns a list of chunks.
    Each chunk is a string.
    """
    if file_path.lower().endswith('.epub'):
        chapters = parse_epub(file_path)
        all_chunks = []
        for chapter in chapters:
            chunks = chunk_text(chapter, target_words=1000)
            all_chunks.extend(chunks)
        return all_chunks
    elif file_path.lower().endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return chunk_text(text, target_words=1000)
    else:
        raise ValueError("Unsupported file format. Only .epub and .txt are supported for now.")
