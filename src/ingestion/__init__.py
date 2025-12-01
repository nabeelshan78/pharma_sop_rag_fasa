import logging
from typing import List
from llama_index.core.schema import TextNode

# Absolute imports ensure stability when running from root
from src.ingestion.loader import SOPLoader
from src.ingestion.cleaner import DocumentCleaner
from src.ingestion.chunker import SOPChunker
from src.ingestion.versioning import VersionManager

# Use centralized logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    FASA Master Pipeline.
    Orchestrates the flow from Raw File -> Vector-Ready Chunks.
    
    Flow:
    1. Versioning: Extract strict metadata (Version, Title) from filename.
    2. Loader: Upload to LlamaCloud -> Get Markdown (ocr/tables).
    3. Cleaner: Remove header/footer noise and cover pages.
    4. Chunker: Split by Markdown Header -> Token Limit -> Inject Context.
    """
    
    def __init__(self):
        logger.info("Initializing FASA Ingestion Pipeline...")
        self.version_manager = VersionManager()
        self.loader = SOPLoader()
        self.cleaner = DocumentCleaner()
        self.chunker = SOPChunker()

    def run(self, file_path: str) -> List[TextNode]:
        """
        Runs the full ingestion pipeline for a single file.
        
        Args:
            file_path: Absolute path to the PDF/DOCX.
            
        Returns:
            List[TextNode]: The final nodes ready for Qdrant insertion.
        """
        try:
            logger.info(f"🚀 STARTING PIPELINE for: {file_path}")
            
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
                logger.warning(f"Step 2 [Loader]: Failed to extract content from {file_path}")
                return []
            logger.info(f"Step 2 [Loader]: Extracted {len(raw_docs)} raw pages.")
            
            # ---------------------------------------------------------
            # STEP 3: CLEANING (Regex Guardrails)
            # ---------------------------------------------------------
            # Removes "Page x of y", "Confidential", and Cover Pages
            clean_docs = self.cleaner.clean_documents(raw_docs)
            if not clean_docs:
                logger.warning("Step 3 [Cleaner]: All content was removed as noise/cover pages.")
                return []
            logger.info(f"Step 3 [Cleaner]: Retained {len(clean_docs)} clean content pages.")
            
            # ---------------------------------------------------------
            # STEP 4: CHUNKING (Structure-Aware)
            # ---------------------------------------------------------
            # Splits by Header (#) and injects "Context Header" strings
            nodes = self.chunker.chunk_documents(clean_docs)
            
            logger.info(f"✅ FINISHED PIPELINE: Generated {len(nodes)} vector-ready chunks.")
            return nodes

        except Exception as e:
            logger.error(f"❌ PIPELINE CRASHED for {file_path}: {str(e)}", exc_info=True)
            # Return empty list to prevent crashing the entire batch process
            return []

# --- EXPORT ---
__all__ = ["IngestionPipeline"]

# --- SELF TEST ---
if __name__ == "__main__":
    import os
    
    # 1. Setup Dummy File
    # (We create a dummy file to test the pipeline flow without needing real PDFs)
    test_file_path = "test_pipeline_doc_v2.0.txt"
    with open(test_file_path, "w") as f:
        f.write("# 1.0 Test Header\nThis is a test content.\nPage 1 of 5")
        
    try:
        # 2. Run Pipeline
        pipeline = IngestionPipeline()
        # Note: SOPLoader requires a real PDF/Extension to trigger LlamaParse usually,
        # but since we handle .txt differently or if LlamaParse fails it might error 
        # unless configured. For this test, ensure you have a REAL file path 
        # or comment out the loader step if just testing logic.
        
        # NOTE: For this test to work, point it to one of your REAL files from the screenshot
        # e.g., real_path = "data/raw_sops/GRT_PROC_English_stamped_Rev06.docx"
        
        print("\n--- Pipeline Initialized. Ready for use. ---")
        print("To test, call: pipeline.run('path/to/your/sop.pdf')")

    except Exception as e:
        print(f"Init failed: {e}")
    finally:
        # Cleanup dummy
        if os.path.exists(test_file_path):
            os.remove(test_file_path)