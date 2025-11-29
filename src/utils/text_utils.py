import re
import unicodedata

def normalize_text(text: str) -> str:
    """
    Normalizes text for consistent searching.
    1. Lowercase
    2. Removes Accents (Important for Italian: 'attività' -> 'attivita')
    3. Removes extra whitespace
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove Accents (NFD Normalization)
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # 3. Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_keywords(query: str) -> str:
    """
    Simple helper to extract potential keywords from a user query.
    Useful if you want to highlight them in the UI later.
    """
    # Remove common punctuation
    clean_query = re.sub(r'[^\w\s]', '', query)
    return normalize_text(clean_query)