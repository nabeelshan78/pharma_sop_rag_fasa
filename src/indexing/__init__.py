# indexing/__init__.py
# Role: The Orchestrator.
# Enhancement: Ties the Embeddings and DB together so the rest of the app doesn't need to know how they work.

import logging
from typing import List
from dotenv import load_dotenv

# Ensure env vars are loaded before anything else
load_dotenv()

from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex

from .embeddings import EmbeddingManager
from .vector_db import QdrantManager

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
from src.core.logger import setup_logger
# This ensures consistent formatting across the whole app
logger = setup_logger(__name__)

class IndexingPipeline:
    """
    High-level API for the Indexing Stage.
    """
    def __init__(self):
        # 1. Configure Embeddings (Global Effect)
        self.embedding_manager = EmbeddingManager()
        self.embedding_manager.get_embedding_model()

        # 2. Configure Vector DB
        self.db_manager = QdrantManager()

    def run(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Takes processed nodes and persists them to the Vector Database.
        """
        if not nodes:
            logger.warning("Indexing Pipeline received empty node list.")
            return None
            
        return self.db_manager.insert_nodes(nodes)

# --- Test Block ---
if __name__ == "__main__":
    # Mock Node for testing
    from llama_index.core.schema import TextNode
    
    pipeline = IndexingPipeline()
    
    mock_node = TextNode(
        text="This is a test of the Pharma SOP system.",
        metadata={
            "sop_name": "Test Protocol",
            "version": "1.0",
            "section": "Intro"
        }
    )
    
    pipeline.run([mock_node])
    print("Test run complete.")