import logging
import os
from typing import List, Optional

from llama_index.core.schema import BaseNode, Document

# Absolute imports for stability
from src.ingestion.loader import SOPLoader
from src.ingestion.cleaner import SOPCleaner
from src.ingestion.chunker import SOPChunker
from src.ingestion.versioning import VersionManager

# Centralized Logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Explicitly export the Pipeline class
__all__ = ["IngestionPipeline"]

class IngestionPipeline:
    """
    FASA Master Ingestion Pipeline.
    
    Responsibilities:
    Orchestrates the transformation of raw binary files (PDF/DOCX) into 
    semantic, citation-ready vector nodes.
    
    Architecture Flow:
    1. Versioning: Extract strict metadata (SOP Title, Version) from filename.
    2. Loader: High-fidelity OCR & Markdown conversion via LlamaParse.
    3. Cleaner: Remove artifacts, TOCs, page numbers, and empty noise.
    4. Chunker: Split by Logical Header, inject citations (Section IDs), and filter.
    """
    
    def __init__(self):
        logger.info(">>>>>>>>>>>>>>>>>      Initializing FASA Ingestion Pipeline components...")
        
        # 1. Metadata Engine
        self.version_manager = VersionManager()
        # 2. Ingestion Engine (Requires LLAMA_CLOUD_API_KEY)
        if not os.getenv("LLAMA_CLOUD_API_KEY"):
            logger.warning("LLAMA_CLOUD_API_KEY not found. Loader may fail.")
        self.loader = SOPLoader()
        # 3. Sanitation Engine
        self.cleaner = SOPCleaner()
        # 4. Semantic Engine
        self.chunker = SOPChunker()
        logger.info(">>>>>>>>>>>>>>>>>      Pipeline components initialized successfully.")

    def run(self, file_path: str) -> List[BaseNode]:
        """
        Executes the full end-to-end pipeline for a single file.
        
        Args:
            file_path (str): Absolute path to the raw SOP file.
            
        Returns:
            List[BaseNode]: A list of LlamaIndex nodes, enriched with:
                            - Content (Cleaned text)
                            - Metadata (Version, Title, Section ID, Path)
                            - Embeddings (Ready for Vector Store)
                            
        Returns [] if any step fails or yields no content.
        """
        try:
            logger.info(f"✅ >>>>>>>>>>>>>>>>>>> STARTING PIPELINE for: {os.path.basename(file_path)}")
            
            # ---------------------------------------------------------
            # STEP 1: METADATA & VERSION CONTROL
            # ---------------------------------------------------------
            # We extract this FIRST so it travels with the document through every step.
            metadata = self.version_manager.extract_metadata(file_path)
            logger.info(f"Step 1 [Metadata]: Detected '{metadata['sop_title']}' v{metadata['version_original']}")
            
            # ---------------------------------------------------------
            # STEP 2: LOADING (LlamaParse)
            # ---------------------------------------------------------
            # Converts PDF binary -> Structured Markdown
            raw_docs = self.loader.load_file(file_path, metadata=metadata)
            
            if not raw_docs:
                logger.error(f"Step 2 [Loader]: Failed to extract content from {file_path}. Skipping.")
                return []
            
            logger.info(f"Step 2 [Loader]: Extracted {len(raw_docs)} raw content segment(s).")
            
            # ---------------------------------------------------------
            # STEP 3: CLEANING (Regex Guardrails)
            # ---------------------------------------------------------
            clean_docs = self.cleaner.clean_documents(raw_docs)
            
            if not clean_docs:
                logger.warning(f"Step 3 [Cleaner]: All content removed as noise for {file_path}. Skipping.")
                return []
                
            logger.info(f"Step 3 [Cleaner]: Sanitization complete.")
            
            # ---------------------------------------------------------
            # STEP 4: CHUNKING (Structure-Aware)
            # ---------------------------------------------------------
            nodes = self.chunker.chunk_documents(clean_docs)
            
            if not nodes:
                logger.warning(f"Step 4 [Chunker]: No valid chunks generated (all filtered out) for {file_path}.")
                return []
            
            logger.info(f"✅ >>>>>>>>>>>>>>>>>>> FINISHED PIPELINE: Generated {len(nodes)} high-quality vector nodes.")
            return nodes

        except Exception as e:
            logger.error(f"❌ >>>>>>>>>>>>>>>>>>> PIPELINE CRASHED for {file_path}: {str(e)}", exc_info=True)
            # Return empty list to prevent crashing the entire batch process
            return []