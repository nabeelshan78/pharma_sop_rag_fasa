# ingestion/loader.py
# Role: strictly handles file I/O and partitioning.

import logging
from pathlib import Path
from typing import List

# Unstructured Imports
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.documents.elements import Element

from src.core.logger import setup_logger
# This ensures consistent formatting across the whole app
logger = setup_logger(__name__)

class DocumentLoader:
    """
    Handles loading of raw files into Unstructured Elements.
    """
    
    @staticmethod
    def load_file(file_path: str) -> List[Element]:
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()
        
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            if ext == ".pdf":
                # strategy='fast' or 'hi_res' depending on need. 
                # 'fast' is better for text-based PDFs.
                return partition_pdf(filename=file_path, strategy='fast')
            elif ext == ".docx":
                return partition_docx(filename=file_path)
            elif ext == ".txt":
                return partition_text(filename=file_path)
            else:
                logger.warning(f"Unsupported file type: {ext}")
                return []
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            raise e