import os
import logging
from typing import List

# --- LlamaIndex Imports ---
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

# --- Qdrant Native Imports ---
from qdrant_client import QdrantClient, models

# Use centralized logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class QdrantManager:
    """
    Manages Qdrant Vector Database interactions.
    
    Features:
    - Hybrid Search (Dense + Sparse BM25).
    - Strict Version Control (Deletes old vectors before insertion).
    - Robust connection handling.
    """
    
    def __init__(self, collection_name: str = "fasa_sops_llama"):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY", None)
        self.collection_name = collection_name

        # 1. Initialize Native Client (For Admin tasks like deletion)
        # Timeout increased to 30s to handle large delete operations
        self.client = QdrantClient(
            url=self.url, 
            api_key=self.api_key, 
            timeout=30.0 
        )
        
        # 2. Check/Create Collection (Prevent startup errors)
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' not found. It will be created automatically on first insert.")
        
        # 3. Initialize LlamaIndex Vector Store with Hybrid Search
        # fastembed_sparse_model="Qdrant/bm25" auto-generates sparse vectors for keyword search
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25", 
            batch_size=20 # Conservative batch size for stability
        )
        
        # 4. Create Storage Context
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def delete_existing_sop(self, sop_title: str):
        """
        STRICT CLEANUP: Removes ALL chunks associated with a specific SOP Title.
        
        Why?
        When uploading 'SOP_Fire_Safety_v2', we want to delete 'SOP_Fire_Safety_v1' 
        AND any previous upload of 'v2' to ensure we have a clean slate.
        
        Args:
            sop_title: The unique title of the SOP (e.g. "GRT PROC English").
        """
        if not self.client.collection_exists(self.collection_name):
            return

        logger.info(f"♻️ Version Control: removing all existing vectors for SOP '{sop_title}'...")

        # Filter: Delete any point where metadata['sop_title'] == sop_title
        filter_condition = models.Filter(
            must=[
                models.FieldCondition(key="sop_title", match=models.MatchValue(value=sop_title))
            ]
        )

        try:
            # Efficient Server-side deletion
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_condition)
            )
            # Log success
            logger.info(f"Cleanup successful. Status: {result.status}")
            
        except Exception as e:
            logger.error(f"Failed to delete old SOP versions: {e}")
            raise e

    def insert_nodes(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Indexes a list of nodes into Qdrant.
        
        Flow:
        1. Identifies the SOP Title from the first node.
        2. WIPES any existing vectors with that title (Anti-Duplication).
        3. Inserts the new clean nodes.
        """
        if not nodes:
            logger.warning("No nodes provided to index.")
            return None

        # 1. Extract Identity from the first node
        # We assume all nodes in this batch belong to the same file (enforced by pipeline)
        first_node = nodes[0]
        
        # Key must match what we set in chunker.py/versioning.py
        sop_title = first_node.metadata.get("sop_title")
        version = first_node.metadata.get("version_original", "Unknown")

        if not sop_title:
            logger.error("❌ Critical: Node missing 'sop_title' metadata. Cannot index safely.")
            return None

        # 2. STRICT DELETE (The "Zero Hallucination" Guardrail)
        # Ensure we don't have v1.0 and v1.1 co-existing.
        self.delete_existing_sop(sop_title)

        # 3. Indexing
        logger.info(f"Indexing {len(nodes)} nodes for '{sop_title}' (v{version}) into Qdrant...")
        try:
            # VectorStoreIndex(...) automatically calls vector_store.add(nodes)
            # It uses the Global Settings.embed_model (configured in main.py or embeddings.py)
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
            logger.info("✅ Indexing Complete.")
            return index
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise e

# --- SELF TEST ---
if __name__ == "__main__":
    print("--- Running Qdrant Connection Test ---")
    try:
        qdrant = QdrantManager()
        info = qdrant.client.get_collections()
        print(f"✅ Connection Successful. Collections found: {info}")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("Ensure Docker container is running: docker run -p 6333:6333 qdrant/qdrant")