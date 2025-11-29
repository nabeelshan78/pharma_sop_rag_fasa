# indexing/vector_db.py
# Role: Manages Qdrant.
# Enhancement: Added version control logic to delete old SOP versions before indexing new ones.
# This ensures only the latest SOP versions are retained in the vector DB.

import os
import logging
from typing import List

# --- LlamaIndex Imports ---
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

# --- Qdrant Native Imports ---
from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

class QdrantManager:
    def __init__(self, collection_name: str = "fasa_sops_llama"):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY", None)
        self.collection_name = collection_name

        # 1. Initialize Native Client (For Admin tasks like deletion)
        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        
        # 2. Initialize LlamaIndex Vector Store with Hybrid Search
        # fastembed_sparse_model="Qdrant/bm25" enables the Keyword search requirement
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25", 
            batch_size=20
        )
        
        # 3. Create Storage Context
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def delete_previous_versions(self, sop_name: str, keep_version: str):
        """
        Removes ANY chunk associated with 'sop_name' that does NOT match 'keep_version'.
        This satisfies the 'Old versions should be archived/removed' requirement.
        """
        if not self.client.collection_exists(self.collection_name):
            return

        logger.info(f"Cleaning up old versions for '{sop_name}' (Keeping v{keep_version})...")

        # Create a filter: SOP Name matches AND Version does NOT match
        filter_condition = models.Filter(
            must=[
                models.FieldCondition(key="sop_name", match=models.MatchValue(value=sop_name))
            ],
            must_not=[
                models.FieldCondition(key="version", match=models.MatchValue(value=str(keep_version)))
            ]
        )

        try:
            # Efficient Server-side deletion
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=filter_condition)
            )
            # Note: Qdrant delete response doesn't always give count, but operation is confirmed
            logger.info(f"Cleanup operation status: {result.status}")
        except Exception as e:
            logger.error(f"Error deleting old versions: {e}")

    def insert_nodes(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Indexes nodes. Handles version cleanup automatically before insertion.
        """
        if not nodes:
            logger.warning("No nodes provided to index.")
            return None

        # 1. Version Control Check
        # We assume all nodes in this batch belong to the same file/version
        first_node = nodes[0]
        sop_name = first_node.metadata.get("sop_name")
        version = first_node.metadata.get("version")

        if sop_name and version:
            self.delete_previous_versions(sop_name, version)

        # 2. Indexing
        logger.info(f"Indexing {len(nodes)} nodes into Qdrant...")
        try:
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
                # embed_model is picked up from Global Settings (set in embeddings.py)
            )
            logger.info("Indexing Complete.")
            return index
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise e