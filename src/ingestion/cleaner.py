import re

def clean_text(text: str) -> str:
    """
    Applies Regex cleaning rules to remove noise (headers, footers, pagination).
    """
    noise_patterns = [
        r"_n_", 
        r"GRUNENTHAL",
        r"^\s*page\s*$" 
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)
    
    header_keywords = [
        r"Number:.*", 
        r"Revision:.*", 
        r"Status:.*", 
        r"Effective Date:.*",
        r"Document No:.*"
    ]
    for pattern in header_keywords:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    footer_patterns = [
        r"(This is an uncontrolled copy valid for.*)",
        r"(Page \d+ of \d+)"
    ]
    for pattern in footer_patterns:
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = text[:match.start()]

    text = re.sub(r"\b\d+\s+of\s+\d+\b", "", text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()