import logging
import os
import nest_asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader

# Apply asyncio patch for stable loop handling
nest_asyncio.apply()

# Load env immediately
load_dotenv()

# Use internal logger
from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPLoader:
    """
    Enterprise Loader for Pharma SOPs.
    
    Responsibilities:
    1. Upload files to LlamaCloud for high-fidelity parsing.
    2. Enforce specific parsing instructions to strip 'header/footer' noise.
    3. Return structured Markdown compatible with 'Structure-Aware Chunking'.
    """
    
    def __init__(self):
        self.api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not self.api_key:
            logger.critical("LLAMA_CLOUD_API_KEY is missing! Cannot process SOPs.")
            raise ValueError("LLAMA_CLOUD_API_KEY required in .env")

        #  Cleaning: Remove headers, footers...
        # We instruct the LLM inside LlamaParse to do this visually.
        self.parsing_instruction = (
            "The provided document is a Pharmaceutical Standard Operating Procedure (SOP). "
            "Reconstruct the document structure exactly as Markdown. "
            "IMPORTANT: Do not output page headers or footers (e.g., 'Page x of y', 'Confidential', 'Effective Date' at the top/bottom). "
            "Only output the main content body, images, and tables."
        )

        # Configure Parser with 'fast' or 'premium' mode based on needs
        # For Pharma Tables, 'premium' is safer if budget allows.
        self.parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=True,
            language="en",
            split_by_page=True, 
            # parsing_instruction=self.parsing_instruction,
            # premium_mode=True,  #  Handle scanned PDFs/Images
            ignore_errors=False
        )

    def load_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Loads a single SOP (PDF/DOCX) and returns a list of Documents (1 per page).
        
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
            
            #  File Formats: Must support PDF, DOCX.
            # We explicitly map .docx to LlamaParse as well for consistent markdown.
            file_extractor = {
                ".pdf": self.parser,
                ".docx": self.parser,
                ".doc": self.parser
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
                # We do a shallow copy to avoid reference issues
                doc_meta = metadata.copy()
                doc_meta["page_label"] = f"Page {i}" # [cite: 7] Page Number tagging
                doc_meta["file_name"] = path_obj.name
                
                doc.metadata = doc_meta
                
                # 2. Sanity Check
                # Drop pages that are just whitespace or extremely short (parsing errors)
                if not doc.text or len(doc.text.strip()) < 10:
                    logger.warning(f"Skipping empty page {i} in {path_obj.name}")
                    continue

                valid_docs.append(doc)
            
            logger.info(f"Successfully parsed {path_obj.name}. Yielded {len(valid_docs)} content pages.")
            return valid_docs

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}", exc_info=True)
            raise e



# --- SELF TEST ---
if __name__ == "__main__":
    # Create a dummy test file to verify connectivity
    # Note: Requires a real .env file with LLAMA_CLOUD_API_KEY
    try:
        loader = SOPLoader()
        print("SOPLoader initialized successfully.")
        # To test real parsing, uncomment below:
        docs = loader.load_file(r"data/raw_sops/GRT_PROC_English_stamped_Rev07 (1).docxNov302025024526.pdf", {"sop_title": "TEST", "version": "1.0"})
        # save to text file for inspection
        with open("test_output.txt", "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(f"--- {doc.metadata.get('page_label', 'Unknown Page')} ---\n")
                f.write(doc.text + "\n\n")
    except Exception as e:
        print(f"Init failed: {e}")