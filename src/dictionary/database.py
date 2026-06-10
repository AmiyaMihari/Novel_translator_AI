import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dictionary.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_term TEXT NOT NULL,
            translated_term TEXT NOT NULL,
            term_type TEXT,
            notes TEXT,
            source_lang TEXT,
            target_lang TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_term(original, translated, term_type, source_lang, target_lang, notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO dictionary (original_term, translated_term, term_type, source_lang, target_lang, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (original, translated, term_type, source_lang, target_lang, notes))
    conn.commit()
    conn.close()

def get_all_terms(source_lang=None, target_lang=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT id, original_term, translated_term, term_type, notes, source_lang, target_lang FROM dictionary WHERE 1=1'
    params = []
    
    if source_lang:
        query += ' AND source_lang = ?'
        params.append(source_lang)
    if target_lang:
        query += ' AND target_lang = ?'
        params.append(target_lang)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "original_term": r[1],
            "translated_term": r[2],
            "term_type": r[3],
            "notes": r[4],
            "source_lang": r[5],
            "target_lang": r[6]
        }
        for r in rows
    ]

def delete_term(term_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM dictionary WHERE id = ?', (term_id,))
    conn.commit()
    conn.close()

def get_dictionary_context(source_lang, target_lang):
    terms = get_all_terms(source_lang, target_lang)
    if not terms:
        return ""
    
    context = "Dictionary / Glossary to maintain consistency:\n"
    for t in terms:
        context += f"- {t['original_term']} -> {t['translated_term']} (Type: {t['term_type']})"
        if t['notes']:
            context += f" Notes: {t['notes']}"
        context += "\n"
    return context
