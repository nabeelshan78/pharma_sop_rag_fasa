# ingestion/cleaner.py
# Role: The "Janitor". It removes headers, footers, and specific regex noise.

import re
from typing import List
from unstructured.documents.elements import Element, Footer, Header, Title

class DocumentCleaner:
    """
    Filters out noise, headers, footers, and irrelevant text artifacts.
    """

    def __init__(self):
        # Regex to remove common PDF artifacts like "Page 1 of 10" or "CONFIDENTIAL"
        self.noise_patterns = [
            r"Page\s+\d+\s+of\s+\d+",  # Page numbering
            r"CONFIDENTIAL",           # Watermarks
            r"^\s*$"                   # Empty lines
        ]

    def clean_text_content(self, text: str) -> str:
        """Applies regex cleaning to a string."""
        cleaned_text = text
        for pattern in self.noise_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        return cleaned_text.strip()

    def clean_elements(self, elements: List[Element]) -> List[Element]:
        """
        Filters unstructured elements. 
        Removes Footer objects and empty text.
        """
        cleaned_elements = []

        for el in elements:
            # 1. Structural Filtering
            if isinstance(el, Footer):
                continue
            
            # 2. Text Cleaning
            raw_text = str(el)
            clean_text = self.clean_text_content(raw_text)

            # 3. Validation
            if len(clean_text) < 5: # Skip extremely short noise
                continue
            
            # Update element text with cleaned version
            el.text = clean_text
            cleaned_elements.append(el)

        return cleaned_elements