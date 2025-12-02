import re
import logging
from typing import List, Dict, Pattern, Any
from llama_index.core.schema import Document

# -----------------------------------------------------------------------------
# Logger Setup
# -----------------------------------------------------------------------------
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    # Fallback for standalone testing
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class DocumentCleaner:
    """
    Regex-based Cleaner for Pharma SOP Markdown.
    
    Responsibilities:
    1. Strip artifacts (Page numbers, "Confidential" footers).
    2. Normalize whitespace to prevent vector drift.
    3. Remove Table of Contents (TOC) lines to prevent "index pollution".
    4. PRESERVE Markdown table structures.
    """

    def __init__(self):
        # Regex to match the specific header format seen in your images.
        # Matches "GRUNENTHAL" followed by optional spaces and the code pattern.
        # We also catch the horizontal separator lines often output by Markdown parsers.
        self.header_patterns = [
            r"GRUNENTHAL\s+[A-Z]{2}-[A-Z]{2}-\d{3}-\d{4}-\d{2}", # Matches GRUNENTHAL AT-GE-577-0002-01
            r"page\s+\d+\s+of\s+\d+", # Matches "page 7 of 10"
            r"This is an uncontrolled copy valid for.*", # Header disclaimer
            r"Printed on:.*", # Footer noise
        ]
        
        # Regex for isolated noise artifacts
        self.noise_patterns = [
            r"^#\s*$",          # Isolated markdown headers "#"
            r"^[-_*]{3,}$",     # Markdown horizontal rules "---"
            r"^\s*>\s*$",       # Empty blockquotes
        ]


        # 1. Removal Patterns (Matches replaced with "")
        self.removal_patterns: Dict[str, Pattern] = {
            # Page numbers (English & Italian)
            # Matches: "Page 1 of 10", "Pagina 1 di 10", "Pag. 1"
            "page_numbers": re.compile(
                r"(?i)((Page|Pagina|Pag\.?)\s+\d+\s+(of|di)\s+\d+)|(\d+\s+(of|di)\s+\d+)|((Page|Pagina)\s+\d+$)", 
                re.MULTILINE
            ),
            
            # Header Metadata artifacts (English & Italian)
            # Matches: "Effective Date", "Data di efficacia", "Approved By", "Approvato da"
            "status_headers": re.compile(
                r"(?i)^(Effective Date|Review Date|Approved By|SOP No|Version|Supersedes|Document No|Data|Data di efficacia|Data di revisione|Approvato da|N\. SOP|Versione|Sostituisce):.*$", 
                re.MULTILINE
            ),
            
            # Signatures & Form Placeholders (English & Italian)
            # Matches: "Signature: ___", "Firma: ___"
            "signatures": re.compile(
                r"(?i)(Signature|Date|Name|Prepared by|Reviewed by|Approved by|Firma|Data|Nome|Preparato da|Revisionato da|Approvato da):\s*[_]{3,}.*", 
                re.MULTILINE
            ),

            # Filled Dates (English & Italian formats)
            # Matches: 06/11/17, 2023-01-01, 01.01.2023
            "filled_dates": re.compile(
                r"(?i)(Date|Data):\s*\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", 
                re.MULTILINE
            ),

            # Legal Disclaimers (English & Italian)
            # Matches: "Uncontrolled copy", "Copia non controllata"
            "disclaimers": re.compile(
                r"(?i)(This is an uncontrolled copy.*)|(Confidential Property of.*)|(No part of this document.*)|(Questa è una copia non controllata.*)|(Proprietà riservata.*)|(Stampato il:.*)", 
                re.MULTILINE
            ),
            
            # TOC Lines (Language Agnostic - looks for dots and numbers)
            "toc_lines": re.compile(r".{5,}\.{4,}\s*\d+\s*$", re.MULTILINE),
            
            # [CRITICAL FIX] Empty Table Rows
            # We ONLY remove rows containing pipes and spaces.
            # We explicitly DO NOT remove rows with hyphens (-) to preserve |---| separators.
            "empty_table_rows": re.compile(r"^\s*\|(\s*\|)+\s*$", re.MULTILINE),
            
            # Visual Separators (___ or ---)
            "separators": re.compile(r"^[-_]{3,}$", re.MULTILINE),
            
            # Empty Markdown Links/Images
            "empty_links": re.compile(r"!\[\]\(\)|\[\]"),
            
            # Non-breaking spaces
            "nbsp": re.compile(r"\xa0"),  
        }
        
        # 2. Formatting Patterns (Require specific replacement logic)
        self.fmt_patterns: Dict[str, Pattern] = {
            # Only match Level 2+ headers (##, ###) to avoid breaking "SOP # 123"
            "header_spacing": re.compile(r"(?<!\n)(#{2,6}\s)"),
            
            # 3+ newlines -> 2 newlines
            "excess_newlines": re.compile(r"\n{3,}"),       
        }

    def clean_text(self, text: str) -> str:
        """
        Applies regex patterns to clean and normalize text.
        """
        if not text:
            return ""
        cleaned_text = text

        # 1. Remove Headers/Footers
        for pattern in self.header_patterns:
            # flags=re.IGNORECASE | re.MULTILINE if needed, 
            # but explicit case is safer for "GRUNENTHAL"
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)

            # 2. Remove isolated noise lines (applied line by line)
            lines = cleaned_text.split('\n')
            cleaned_lines = []
            for line in lines:
                is_noise = False
                for noise_pat in self.noise_patterns:
                    if re.match(noise_pat, line.strip()):
                        is_noise = True
                        break
                if not is_noise:
                    cleaned_lines.append(line)
            
            cleaned_text = "\n".join(cleaned_lines)

            # 3. Collapse multiple newlines (created by removing headers) into two
            cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        # 1. Apply Removal Patterns
        for name, pattern in self.removal_patterns.items():
            cleaned_text = pattern.sub("", cleaned_text)
        # 2. Fix Header Spacing: Ensure headers are preceded by double newlines
        cleaned_text = self.fmt_patterns["header_spacing"].sub(r"\n\n\1", cleaned_text)
        # 3. Collapse Excess Newlines: Replace 3+ newlines with exactly 2
        cleaned_text = self.fmt_patterns["excess_newlines"].sub("\n\n", cleaned_text)
        return cleaned_text.strip()

    def clean_documents(self, documents: List[Document]) -> List[Document]:
        """
        Iterates through documents, drops cover pages, cleans text, 
        and creates new Document objects to ensure immutability safety.
        """
        cleaned_docs = []
        total_chars_removed = 0
        
        # We assume the documents are passed in order (Page 1, Page 2, etc.)
        for i, doc in enumerate(documents):
            # 1. Business Logic: Drop Cover Page
            if i == 0:
                fname = doc.metadata.get('file_name', 'Unknown')
                logger.info(f"Dropped Cover Page (Index 0) from {fname}")
                continue

            original_text = doc.text or ""  # Handle None safety
            new_text = self.clean_text(original_text)

            # If a page contained only noise (disclaimers), it might be empty now.
            if len(new_text.strip()) <= 50:
                logger.warning(f"Dropped empty page after cleaning: {doc.metadata.get('page_label', 'unknown')}")
                continue

            # We create a new instance to avoid modifying the original list references
            new_metadata = doc.metadata.copy()
            
            new_doc = Document(
                text=new_text,
                metadata=new_metadata,
                excluded_embed_metadata_keys=doc.excluded_embed_metadata_keys,
                excluded_llm_metadata_keys=doc.excluded_llm_metadata_keys,
                relationships=doc.relationships
            )

            cleaned_docs.append(new_doc)
            total_chars_removed += (len(original_text) - len(new_text))

        logger.info(f"Cleanup Complete. Processed {len(documents)} -> {len(cleaned_docs)} pages. Removed {total_chars_removed} chars of noise.")
        return cleaned_docs
    



if __name__ == "__main__":
    import json
    import os
    import sys


    INPUT_FILE = "test_outputs/2_test_documents.jsonl"
    OUTPUT_FILE = "test_outputs/2_test_documents_cleaned.jsonl"

    print(f"--- FASA Cleaner Diagnostic ---")

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)

    # 1. Load Documents
    docs_to_clean = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        doc = Document.from_json(line.strip())
                        docs_to_clean.append(doc)
                    except Exception as e:
                        logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
        
        print(f"Loaded {len(docs_to_clean)} documents.")

    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        sys.exit(1)

    # 2. Run Cleaning Logic
    cleaner = DocumentCleaner()
    cleaned_docs = cleaner.clean_documents(docs_to_clean)

    # 3. Save Output
    def save_documents_jsonl(docs, path="documents.jsonl"):
        with open(path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps({
                    "text": doc.text,
                    "metadata": doc.metadata
                }, ensure_ascii=False))
                f.write("\n")
    
    try:
        save_documents_jsonl(cleaned_docs, path=OUTPUT_FILE)
        print(f"Success! Saved {len(cleaned_docs)} cleaned documents to: {OUTPUT_FILE}")
        
        # 4. FIXED Diff Preview (Align Indices)
        if len(docs_to_clean) > 1 and len(cleaned_docs) > 0:
            # Since clean_documents drops index 0, the first cleaned doc (index 0)
            # corresponds to the original doc at index 1.
            
            orig_doc = docs_to_clean[1] 
            clean_doc = cleaned_docs[0]

            print("\n--- 🔍 Diff Preview (Comparing Correct Pages) ---")
            print(f"Original (Page {orig_doc.metadata.get('page_label', '?')}) Length: {len(orig_doc.text)} chars")
            print(f"Cleaned  (Page {clean_doc.metadata.get('page_label', '?')}) Length: {len(clean_doc.text)} chars")
            
            diff = len(orig_doc.text) - len(clean_doc.text)
            if diff > 0:
                print(f"Noise Removed: {diff} chars")
            elif diff < 0:
                print(f"Text Added: {abs(diff)} chars (Check header spacing regex)")
            else:
                print(f"ℹNo change in length.")
                
            print("\n--- Snippet Check (Bottom 100 chars) ---")
            print(f"ORIGINAL:\n{orig_doc.text[-100:].replace(chr(10), ' ')}")
            print(f"CLEANED: \n{clean_doc.text[-100:].replace(chr(10), ' ')}")

    except Exception as e:
        logger.error(f"Failed to write output file: {e}")