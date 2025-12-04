import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# LlamaIndex Ecosystem
from llama_parse import LlamaParse
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader

# Load environment variables
load_dotenv()

# Internal Logger
from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPLoader:
    """
    Loader for Pharmaceutical SOPs.
    """
    
    def __init__(self):
        self.api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            logger.critical("LLAMA_CLOUD_API_KEY is missing! Cannot process SOPs.")
            raise ValueError("LLAMA_CLOUD_API_KEY required in .env file.")

        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=True,
            language="en",
            split_by_page=False, 
            ignore_errors=False
        )

    def load_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Loads a single SOP and returns a list containing the structured content.
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            logger.error(f"File not found at path: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        if metadata is None:
            metadata = {}

        try:
            # Configure File Extractor mapping
            file_extractor = {
                ".pdf": self.parser,
                ".docx": self.parser,
                ".doc": self.parser,
                ".docm": self.parser,
                ".txt": self.parser
            }
            # Load Data
            reader = SimpleDirectoryReader(
                input_files=[str(path_obj)],
                file_extractor=file_extractor
            )
            
            documents = reader.load_data()    
            if not documents:
                logger.warning(f"LlamaParse returned no content for {path_obj.name}")
                return []
            
            valid_docs = []
            for doc in documents:
                if not doc.text or len(doc.text.strip()) < 10:
                    logger.warning(f"Skipping empty document segment in {path_obj.name}")
                    continue
                doc.metadata.update(metadata)
                doc.metadata["parsed_by"] = "LlamaParse_Markdown"
                valid_docs.append(doc)
            
            logger.info(f"Successfully parsed {path_obj.name}. Extracted {len(valid_docs)} document segment(s).")
            return valid_docs

        except Exception as e:
            logger.error(f"CRITICAL parsing error for {file_path}: {e}", exc_info=True)
            raise e




































# if __name__ == "__main__":
#     import json
#     def save_documents_jsonl(docs, path="test_outputs/debug_docs.jsonl"):
#         os.makedirs(os.path.dirname(path), exist_ok=True)
#         with open(path, "w", encoding="utf-8") as f:
#             for doc in docs:
#                 entry = {
#                     "text_preview": doc.text,
#                     "full_text_length": len(doc.text),
#                     "metadata": doc.metadata
#                 }
#                 f.write(json.dumps(entry, ensure_ascii=False) + "\n")
#         print(f"Saved debug output to {path}")

#     try:
#         loader = SOPLoader()
#         test_metadata = {
#             'sop_title': 'AT-GE-577-0002', 
#             'version_original': '1.0', 
#             'file_name': 'test_sop.pdf', 
#             'upload_timestamp': '2025-12-04T10:00:00'
#         }
        
#         test_file_path = "data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051.pdf" 
#         if not os.path.exists(test_file_path):
#             print(f"Test file not found at {test_file_path}. Please place a file there to test.")
#         else:
#             docs = loader.load_file(test_file_path, metadata=test_metadata)
#             save_documents_jsonl(docs)
#             print("\n--- Content Preview ---")
#             print(docs[0].text[:500])
#             print("\n--- Metadata ---")
#             print(docs[0].metadata)

#     except Exception as e:
#         print(f"Test Execution Failed: {e}")