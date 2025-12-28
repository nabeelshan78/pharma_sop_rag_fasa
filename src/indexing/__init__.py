import logging
from typing import List, Optional

from llama_index.core.schema import TextNode
from llama_index.core import VectorStoreIndex

# Absolute imports
from src.indexing.embeddings import EmbeddingManager
from src.indexing.vector_db import QdrantManager

# =========================================================================================

class IndexingPipeline:
    """
    FASA Indexing Orchestrator (Ollama Edition).
    """
    
    def __init__(self):
        print("Initializing FASA Indexing Pipeline (Ollama Backed)...")
        
        # 1. Force-configure Global Embeddings (Ollama)
        # This ensures all subsequent LlamaIndex operations use 'nomic-embed-text'
        EmbeddingManager.configure_global_settings()
        
        # 2. Initialize connection to Qdrant
        self.db_manager = QdrantManager()

    def run(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
        if not nodes:
            print("Indexing Pipeline received empty node list. Skipping.")
            return None
        return self.db_manager.insert_nodes(nodes)