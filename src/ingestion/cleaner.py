import re
import logging
from typing import List, Dict, Pattern
from llama_index.core.schema import Document

from src.core.logger import setup_logger

logger = setup_logger(__name__)

class DocumentCleaner:
    """
    Regex-based Cleaner for Pharma SOP Markdown.
    Handles artifact removal and fixes Pydantic Immutability errors 
    by regenerating Document objects.
    """

    def __init__(self):
        # 1. Removal Patterns: These matches will be replaced with an empty string ""
        self.removal_patterns: Dict[str, Pattern] = {
            "page_numbers": re.compile(
                r"(?i)(Page\s+\d+\s+of\s+\d+)|(\d+\s+of\s+\d+)|(Page\s+\d+$)", 
                re.MULTILINE
            ),
            "status_headers": re.compile(
                r"(?i)^(Effective Date|Review Date|Approved By|SOP No|Version):.*$", 
                re.MULTILINE
            ),
            "disclaimers": re.compile(
                r"(?i)(This is an uncontrolled copy.*)|(Confidential Property of.*)|(No part of this document.*)|(Printed on:.*)", 
                re.MULTILINE
            ),
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
        if index != 0:
            return False
        return "Document Information" in text or "SOP Title" in text

    def clean_text(self, text: str) -> str:
        """Applies regex patterns to clean and normalize text."""
        if not text:
            return ""

        cleaned_text = text

        # Apply removal patterns
        for _, pattern in self.removal_patterns.items():
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
            # 1. Check for Cover Page
            if self._is_cover_page(i, doc.text):
                logger.info(f"🗑️ Dropped Cover Page (Index 0) from {doc.metadata.get('filename', 'Unknown')}")
                continue

            # 2. Clean Text
            original_text = doc.text
            new_text = self.clean_text(original_text)

            # Skip empty pages after cleaning
            if len(new_text.strip()) <= 10:
                logger.warning(f"Dropped empty page: {doc.metadata.get('page_label', 'unknown')}")
                continue

            # 3. Create New Metadata (Fix URL encoded filenames)
            new_metadata = doc.metadata.copy()
            if "filename" in new_metadata:
                new_metadata["filename"] = new_metadata["filename"].replace("%20", " ")

            # 4. Create New Document (Pydantic Safety Fix)
            # We must create a new object to bypass 'property has no setter' errors
            new_doc = Document(
                text=new_text,
                metadata=new_metadata,
                excluded_embed_metadata_keys=doc.excluded_embed_metadata_keys,
                excluded_llm_metadata_keys=doc.excluded_llm_metadata_keys,
                relationships=doc.relationships
            )

            cleaned_docs.append(new_doc)
            total_chars_removed += (len(original_text) - len(new_text))

        logger.info(f"🧹 Cleanup Complete. Processed {len(documents)} pages. Removed {total_chars_removed} chars.")
        return cleaned_docs