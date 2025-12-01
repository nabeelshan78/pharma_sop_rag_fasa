import logging
import os
import nest_asyncio
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader

# Apply asyncio fix for notebooks/scripts
nest_asyncio.apply()

# Load env immediately
load_dotenv()

from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPLoader:
    """
    Specialized Loader for Pharmaceutical Standard Operating Procedures (SOPs).
    
    Features:
    - Uses LlamaParse (Premium) for table extraction.
    - Custom parsing instructions to strip Headers/Footers.
    - Preserves Markdown structure for Hierarchy (5.1, 5.1.1).
    - Retains Page Numbers in metadata.
    """
    
    def __init__(self):
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            logger.critical("LLAMA_CLOUD_API_KEY is missing! Cannot process SOPs.")
            raise ValueError("LLAMA_CLOUD_API_KEY required in .env")
        
        # 1. DEFINE INSTRUCTION
        # We explicitly tell the model how to handle the Pharma noise.
        parsing_instruction = (
            "The provided document is a Pharmaceutical Standard Operating Procedure (SOP). "
            "It contains strict formatting, tables, and process flows. "
            "1. Strictly remove all page headers and footers (e.g., 'Page 1 of 10', 'Effective Date', 'SOP-XYZ'). "
            "2. Extract all tables as clean Markdown tables. "
            "3. If a flowchart or diagram is present, describe the process flow in text steps. "
            "4. Preserve the numbering hierarchy (e.g., 5.3, 5.3.1) exactly with proper markdown format."
        )

        # 2. CONFIGURE PARSER
        self.parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",  # Essential for LLM comprehension
            verbose=True,
            language="en",
            split_by_page=True,      # Keeps pages separate so we can cite Page #
            # premium_mode=True,       # Required for high-fidelity table extraction
            # parsing_instruction=parsing_instruction
        )

    def load_file(self, file_path: str, metadata: Optional[Dict] = None) -> List[Document]:
        """
        Loads a single SOP PDF and returns a list of Documents (usually 1 per page).
        
        Args:
            file_path: Path to the PDF.
            metadata: Dict containing 'sop_title', 'version', etc.
        """
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        # Default metadata if none provided
        if metadata is None:
            metadata = {}

        try:
            logger.info(f"LlamaParsing SOP: {path_obj.name}...")
            
            # Use SimpleDirectoryReader to wrap LlamaParse
            file_extractor = {".pdf": self.parser}
            
            reader = SimpleDirectoryReader(
                input_files=[str(path_obj)],
                file_extractor=file_extractor
            )
            
            # Load data - this returns a list of Document objects (ordered by page)
            documents = reader.load_data()
            
            # 3. ENRICH METADATA
            # We iterate through every page/doc and inject the SOP-level metadata
            valid_docs = []
            
            # FIX: Use enumerate to guarantee correct "Page X" sequence
            for i, doc in enumerate(documents, start=1):
                
                # Update doc metadata with what we passed in (Title, Version)
                doc.metadata.update(metadata)
                
                # OVERWRITE page_label to ensure "Page 1", "Page 2" format
                doc.metadata["page_label"] = f"Page {i}"
                
                # Add filename manually if SimpleDirectoryReader missed it (redundancy)
                if "file_name" not in doc.metadata:
                    doc.metadata["file_name"] = path_obj.name

                # Basic sanity check: Don't ingest empty pages
                if doc.text and len(doc.text.strip()) > 10:
                    valid_docs.append(doc)
            
            logger.info(f"Successfully parsed {path_obj.name}. Extracted {len(valid_docs)} pages.")
            return valid_docs

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            raise e



        




# # ingestion/loader.py
# # Role: strictly handles file I/O and partitioning.

# import logging
# from pathlib import Path
# from typing import List

# # Unstructured Imports
# from unstructured.partition.pdf import partition_pdf
# from unstructured.partition.docx import partition_docx
# from unstructured.partition.text import partition_text
# from unstructured.documents.elements import Element

# from src.core.logger import setup_logger
# # This ensures consistent formatting across the whole app
# logger = setup_logger(__name__)

# class DocumentLoader:
#     """
#     Handles loading of raw files into Unstructured Elements.
#     """
    
#     @staticmethod
#     def load_file(file_path: str) -> List[Element]:
#         path_obj = Path(file_path)
#         ext = path_obj.suffix.lower()
        
#         if not path_obj.exists():
#             raise FileNotFoundError(f"File not found: {file_path}")

#         try:
#             if ext == ".pdf":
#                 # strategy='fast' or 'hi_res' depending on need. 
#                 # 'fast' is better for text-based PDFs.
#                 return partition_pdf(filename=file_path, strategy='fast')
#             elif ext == ".docx":
#                 return partition_docx(filename=file_path)
#             elif ext == ".txt":
#                 return partition_text(filename=file_path)
#             else:
#                 logger.warning(f"Unsupported file type: {ext}")
#                 return []
#         except Exception as e:
#             logger.error(f"Failed to load {file_path}: {e}")
#             raise e