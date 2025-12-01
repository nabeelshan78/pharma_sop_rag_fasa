import re
import logging
from typing import List, Dict, Pattern
from llama_index.core.schema import Document
import os

# Ensure we can import the logger even if running as a script
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class DocumentCleaner:
    """
    Regex-based Cleaner for Pharma SOP Markdown.
    
    Responsibilities:
    1. Strip artifacts (Page numbers, "Confidential" footers) that survive OCR.
    2. Normalize whitespace to prevent vector drift.
    3. Remove Table of Contents (TOC) lines to prevent "index pollution".
    """

    def __init__(self):
        # 1. Removal Patterns: These matches will be replaced with an empty string ""
        self.removal_patterns: Dict[str, Pattern] = {
            "page_numbers": re.compile(
                r"(?i)(Page\s+\d+\s+of\s+\d+)|(\d+\s+of\s+\d+)|(Page\s+\d+$)", 
                re.MULTILINE
            ),
            # Anchored to start of line (^) to avoid deleting mid-sentence words
            "status_headers": re.compile(
                r"(?i)^(Effective Date|Review Date|Approved By|SOP No|Version|Supersedes):.*$", 
                re.MULTILINE
            ),
            "disclaimers": re.compile(
                r"(?i)(This is an uncontrolled copy.*)|(Confidential Property of.*)|(No part of this document.*)|(Printed on:.*)", 
                re.MULTILINE
            ),
            # Matches "Introduction ........ 5" type TOC lines
            "toc_lines": re.compile(r".{5,}\.{4,}\s*\d+\s*$", re.MULTILINE),
            "empty_table_rows": re.compile(r"^\s*\|[\s\-\|]*\|\s*$", re.MULTILINE),
            "separators": re.compile(r"^[-_]{3,}$", re.MULTILINE),
            "empty_links": re.compile(r"!\[\]\(\)|\[\]"),
            "nbsp": re.compile(r"\xa0"),  # Non-breaking spaces
        }

        # 2. Formatting Patterns: These require specific replacement logic
        self.fmt_patterns = {
            "header_spacing": re.compile(r"(?<!\n)(#+\s)"), # Headers not preceded by newline
            "excess_newlines": re.compile(r"\n{3,}"),       # 3+ newlines
        }

    def _is_cover_page(self, index: int, text: str) -> bool:
        """Determines if the document is a cover page based on index and content."""
        # Expanded logic: Cover pages often have little content but specific keywords
        if index == 0:
            if "Document Information" in text or "SOP Title" in text or len(text) < 200:
                return True
        return False

    def clean_text(self, text: str) -> str:
        """Applies regex patterns to clean and normalize text."""
        if not text:
            return ""

        cleaned_text = text

        # Apply removal patterns
        for name, pattern in self.removal_patterns.items():
            cleaned_text = pattern.sub("", cleaned_text)

        # Fix Header Spacing: Ensure headers are preceded by double newlines
        cleaned_text = self.fmt_patterns["header_spacing"].sub(r"\n\n\1", cleaned_text)

        # Collapse Excess Newlines: Replace 3+ newlines with exactly 2
        cleaned_text = self.fmt_patterns["excess_newlines"].sub("\n\n", cleaned_text)

        return cleaned_text.strip()

    def clean_documents(self, documents: List[Document]) -> List[Document]:
        """
        Iterates through documents, drops cover pages, cleans text, 
        and creates new Document objects to ensure immutability safety.
        """
        cleaned_docs = []
        total_chars_removed = 0

        for i, doc in enumerate(documents):
            # # 1. Check for Cover Page
            # if self._is_cover_page(i, doc.text):
            #     # Use file_name instead of filename to match loader.py
            #     fname = doc.metadata.get('file_name', 'Unknown')
            #     logger.info(f"Dropped Cover Page (Index 0) from {fname}")
            #     continue

            # 2. Clean Text
            original_text = doc.text
            new_text = self.clean_text(original_text)

            # Skip empty pages after cleaning
            if len(new_text.strip()) <= 15:
                logger.warning(f"Dropped empty page after cleaning: {doc.metadata.get('page_label', 'unknown')}")
                continue

            # 3. Create New Metadata
            new_metadata = doc.metadata.copy()
            # Fix URL encoded filenames if present
            if "file_name" in new_metadata:
                new_metadata["file_name"] = new_metadata["file_name"].replace("%20", " ")

            # 4. Create New Document (Pydantic Safety Fix)
            new_doc = Document(
                text=new_text,
                metadata=new_metadata,
                excluded_embed_metadata_keys=doc.excluded_embed_metadata_keys,
                excluded_llm_metadata_keys=doc.excluded_llm_metadata_keys,
                relationships=doc.relationships
            )

            cleaned_docs.append(new_doc)
            total_chars_removed += (len(original_text) - len(new_text))

        logger.info(f"🧹 Cleanup Complete. Processed {len(documents)} -> {len(cleaned_docs)} pages. Removed {total_chars_removed} chars of noise.")
        return cleaned_docs

# --- MAIN SCRIPT FOR TESTING & SAVING OUTPUT ---
if __name__ == "__main__":
    print("--- Running Cleaner Diagnostic ---")
    
    # 1. Simulate a messy Pharma Page (Markdown format)
    messy_text = """
# Sample SOP Document
    """
    
    # 2. Create a Mock Document
    doc = Document(
        text=messy_text,
        metadata={"file_name": "TEST_SOP.pdf", "page_label": "Page 1"}
    )
    
    # 3. Initialize Cleaner and Run
    cleaner = DocumentCleaner()
    cleaned_docs = cleaner.clean_documents([doc])
    
    if cleaned_docs:
        final_text = cleaned_docs[0].text
        
        # 4. Save to File
        output_path = "debug_cleaning_output.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("--- ORIGINAL ---\n")
            f.write(messy_text)
            f.write("\n\n--- CLEANED ---\n")
            f.write(final_text)
            
        print(f"\n✅ Success! Cleaned text saved to: {output_path}")
        print("-" * 30)
        print("PREVIEW OF CLEANED TEXT:")
        print(final_text)
        print("-" * 30)
    else:
        print("❌ Error: Document was removed entirely (empty result).")