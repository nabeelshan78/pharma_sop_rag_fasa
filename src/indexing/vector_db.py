import os
import logging
from typing import List, Optional

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
    Now includes 'Downgrade Protection'.
    """
    
    def __init__(self, collection_name: str = "fasa_sops_llama"):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY", None)
        self.collection_name = collection_name

        self.client = QdrantClient(
            url=self.url, 
            api_key=self.api_key, 
            timeout=30.0 
        )
        
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' not found. It will be created automatically.")
        
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25", 
            batch_size=20
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def _is_safe_to_update(self, sop_title: str, new_version_float: float) -> bool:
        """
        GUARDRAIL: Checks if the new file is older than what we already have.
        Returns:
            True: If safe to update (New >= Old OR Old doesn't exist).
            False: If we are trying to downgrade (New < Old).
        """
        try:
            # 1. Search for 1 chunk of the existing SOP
            filter_condition = models.Filter(
                must=[
                    models.FieldCondition(key="sop_title", match=models.MatchValue(value=sop_title))
                ]
            )
            
            res = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=1,
                with_payload=True
            )
            
            # If no results, it's a brand new SOP. Safe to insert.
            if not res[0]:
                return True
                
            # 2. Extract Existing Version
            existing_payload = res[0][0].payload
            # We use 0.0 as default if key is missing
            existing_version = existing_payload.get("metadata", {}).get("version_float", 0.0)
            
            logger.info(f"Comparing Versions for '{sop_title}': Existing={existing_version} vs New={new_version_float}")

            # 3. Compare
            if new_version_float < existing_version:
                logger.warning(f"⛔ BLOCKED: Attempted to downgrade '{sop_title}' from v{existing_version} to v{new_version_float}.")
                return False
                
            return True

        except Exception as e:
            logger.error(f"Version check failed: {e}")
            # If check fails, we default to blocking to be safe
            return False

    def delete_existing_sop(self, sop_title: str):
        """
        Removes ALL chunks associated with a specific SOP Title.
        """
        if not self.client.collection_exists(self.collection_name):
            return

        logger.info(f"♻️  Removing old vectors for SOP '{sop_title}'...")
        
        filter_condition = models.Filter(
            must=[
                models.FieldCondition(key="sop_title", match=models.MatchValue(value=sop_title))
            ]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(filter=filter_condition)
        )

    def insert_nodes(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
        """
        Indexes nodes with Downgrade Protection.
        """
        if not nodes:
            return None

        first_node = nodes[0]
        sop_title = first_node.metadata.get("sop_title")
        # Ensure we treat 'None' as 0.0
        new_version_float = float(first_node.metadata.get("version_float", 0.0))

        if not sop_title:
            logger.error("❌ Critical: Node missing 'sop_title'. Cannot index.")
            return None

        # --- STEP 1: SAFETY CHECK ---
        if not self._is_safe_to_update(sop_title, new_version_float):
            # We return None to signal failure to the pipeline
            logger.error(f"❌ UPDATE REJECTED: Database has a newer version of '{sop_title}'.")
            return None

        # --- STEP 2: WIPE OLD VERSION ---
        self.delete_existing_sop(sop_title)

        # --- STEP 3: INSERT NEW VERSION ---
        try:
            logger.info(f"Indexing {len(nodes)} nodes for '{sop_title}' (v{new_version_float})...")
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
            logger.info("✅ Indexing Complete.")
            return index
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise e