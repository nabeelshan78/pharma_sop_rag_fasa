import logging
from typing import List, Optional
from dotenv import load_dotenv

# Ensure env vars are loaded before anything else
load_dotenv()

from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex

# Absolute imports for stability
from src.indexing.embeddings import EmbeddingManager
from src.indexing.vector_db import QdrantManager

# Use centralized logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class IndexingPipeline:
    """
    FASA Indexing Orchestrator.
    
    Responsibilities:
    1. Force-configure Global Embeddings (Google Gemini) on startup.
    2. Initialize connection to Qdrant.
    3. Route processed nodes into the database.
    """
    
    def __init__(self):
        logger.info("Initializing FASA Indexing Pipeline...")

        # 1. Configure Embeddings (Global Effect)
        # CRITICAL: We must call this to override OpenAI defaults with Gemini.
        EmbeddingManager.configure_global_settings()

        # 2. Configure Vector DB Manager
        self.db_manager = QdrantManager()

    def run(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
        """
        Takes processed nodes and persists them to the Vector Database.
        """
        if not nodes:
            logger.warning("Indexing Pipeline received empty node list. Skipping.")
            return None
            
        # The db_manager handles the "Delete Old Version -> Insert New" logic
        return self.db_manager.insert_nodes(nodes)

# --- EXPORT ---
__all__ = ["IndexingPipeline"]

# --- SELF TEST ---
if __name__ == "__main__":
    print("--- Running Indexing Pipeline Diagnostic ---")
    
    # 1. Create Mock Node (Matching the strict schema of chunker.py)
    mock_node = TextNode(
        text="This is a test of the Pharma SOP system integration.",
        metadata={
            "sop_title": "TEST_INTEGRATION_SOP",  # Key used by vector_db.py
            "version_original": "1.0",           # Key used by vector_db.py
            "file_name": "test_file.pdf",
            "page_label": "Page 1"
        }
    )
    
    try:
        # 2. Initialize
        pipeline = IndexingPipeline()
        
        # 3. Run Insertion
        result = pipeline.run([mock_node])
        
        if result:
            print("✅ Success: Pipeline orchestrated Embedding + DB Insertion.")
        else:
            print("⚠️ Warning: Pipeline ran but returned None (Check logs).")
            
    except Exception as e:
        print(f"❌ Pipeline Failed: {e}")