import os
from pathlib import Path
import json
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader

# Load env immediately
load_dotenv()

# Use internal logger
from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPLoader:
    """
    Loader for Pharma SOPs.
    
    Responsibilities:
    1. Upload files to LlamaCloud for high-fidelity parsing.
    2. Return structured Markdown for 'Structure-Aware Chunking'.
    """
    
    def __init__(self):
        self.api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            logger.critical("LLAMA_CLOUD_API_KEY is missing! Cannot process SOPs.")
            raise ValueError("LLAMA_CLOUD_API_KEY required in .env")

        # Configure Parser for Markdown output
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=True,
            language=["en", "it"],
            split_by_page=True, 
            ignore_errors=False
        )

    def load_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Loads a single SOP and returns a list of Documents (1 per page).
        
        Args:
            file_path: Absolute path to the file.
            metadata: Enriched metadata from versioning.py (Title, Version, etc.)
        """
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        # Default metadata
        if metadata is None:
            metadata = {}

        try:
            logger.info(f"Uploading & Parsing SOP: {path_obj.name}...")
            #  File Formats: Must support PDF, DOCX. DOC, TXT
            file_extractor = {
                ".pdf": self.parser,
                ".docx": self.parser,
                ".doc": self.parser,
                ".txt": self.parser
            }
            
            # Use SimpleDirectoryReader to wrap the extraction logic
            reader = SimpleDirectoryReader(
                input_files=[str(path_obj)],
                file_extractor=file_extractor
            )
            # Load data - returns List[Document]
            documents = reader.load_data()
            
            valid_docs = []
            # Enumerate to track page numbers locally relative to this file
            for i, doc in enumerate(documents, start=1):
                # 1. Inject Metadata
                doc_meta = metadata.copy()
                doc_meta["page_label"] = f"Page {i}"
                doc.metadata = doc_meta
                
                # 2. Sanity Check
                # Drop pages that are just whitespace or extremely short (parsing errors)
                if not doc.text or len(doc.text.strip()) < 30:
                    logger.warning(f"Skipping empty page {i} in {path_obj.name}")
                    continue
                valid_docs.append(doc)
            
            logger.info(f"Successfully parsed {path_obj.name}. Yielded {len(valid_docs)} content pages.")
            return valid_docs

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}", exc_info=True)
            raise e





if __name__ == "__main__":
    def save_documents_jsonl(docs, path="documents.jsonl"):
        with open(path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps({
                    "text": doc.text,
                    "metadata": doc.metadata
                }, ensure_ascii=False))
                f.write("\n")
    try:
        loader = SOPLoader()
        meta_data = {
            'sop_title': 'AT-GE-577-0002', 
            'version_original': '01', 
            'version_float': 1.0, 
            'file_name': 'AT-GE-577-0002-01.pdfNov302025024051', 
            'file_path': 'data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051'
        }
        docs = loader.load_file("data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051.pdf", metadata=meta_data)
        save_documents_jsonl(docs, path="test_outputs/test_documents.jsonl")
        
        # save to text file for inspection
        with open("test_outputs/test_documents.txt", "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(f"--- {doc.metadata.get('page_label', 'Unknown Page')} ---\n")
                f.write(doc.text + "\n\n")
    except Exception as e:
        print(f"Init failed: {e}")