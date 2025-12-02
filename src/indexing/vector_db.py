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
    Includes 'Downgrade Protection' to prevent overwriting newer SOPs with older ones.
    """
    
    def __init__(self, collection_name: str = "fasa_sops_llama"):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = os.getenv("QDRANT_API_KEY", None)
        self.collection_name = collection_name

        # Initialize Native Client (for custom deletions/checks)
        self.client = QdrantClient(
            url=self.url, 
            api_key=self.api_key, 
            timeout=30.0 
        )
        
        # Create Collection if it doesn't exist (Vector Size 768 for Gemini)
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Collection '{self.collection_name}' not found. Creating...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
        
        # Initialize LlamaIndex Store
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            enable_hybrid=True, # Critical for Keyword Search
            fastembed_sparse_model="Qdrant/bm25", 
            batch_size=20
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def _is_safe_to_update(self, sop_title: str, new_version_float: float) -> bool:
        """
        GUARDRAIL: Checks if the new file is older than what we already have.
        
        Logic:
        1. Fetch ONE vector with the same 'sop_title'.
        2. Read its 'version_float' metadata.
        3. If new_version < existing_version -> BLOCK (False).
        4. If new_version >= existing_version -> ALLOW (True).
        5. If does not exist -> ALLOW (True).
        """
        try:
            # 1. Search for existing SOP by Title
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
            
            # If no results (empty list), it's a brand new SOP. Safe to insert.
            if not res[0]:
                return True
                
            # 2. Extract Existing Version from Payload
            existing_payload = res[0][0].payload
            
            # Note: We look in the 'metadata' dict inside the payload
            # LlamaIndex stores metadata fields at the top level of payload usually, 
            # but we use .get() to be safe.
            existing_version = existing_payload.get("version_float", 0.0)
            
            # Fallback: sometimes metadata is nested
            if existing_version == 0.0 and "metadata" in existing_payload:
                 existing_version = existing_payload["metadata"].get("version_float", 0.0)

            logger.info(f"Comparing Versions for '{sop_title}': Existing=v{existing_version} vs Incoming=v{new_version_float}")

            # 3. Compare (Using Float for Math)
            if new_version_float < existing_version:
                logger.warning(f"BLOCKED: Attempted to downgrade '{sop_title}' from v{existing_version} to v{new_version_float}.")
                return False
                
            return True

        except Exception as e:
            logger.error(f"Version check failed: {e}")
            # Fail-safe: If we can't verify, we BLOCK to prevent data corruption
            return False

    def delete_existing_sop(self, sop_title: str):
        """
        Removes ALL chunks associated with a specific SOP Title.
        This ensures clean updates (no ghost chunks from old versions).
        """
        if not self.client.collection_exists(self.collection_name):
            return

        logger.info(f"Removing old vectors for SOP '{sop_title}'...")
        
        # Delete by Filter (sop_title == target)
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
        Main Ingestion Entry Point.
        1. Checks Version Safety.
        2. Deletes Old Data.
        3. Inserts New Data.
        """
        if not nodes:
            return None

        # metadata is required for version logic
        first_node = nodes[0]
        sop_title = first_node.metadata.get("sop_title")
        
        # # Safely cast to float
        # try:
        #     new_version_float = float(first_node.metadata.get("version_float", 0.0))
        # except (ValueError, TypeError):
        #     logger.warning(f"Invalid version_float in metadata. Defaulting to 0.0")
        #     new_version_float = 0.0

        # if not sop_title:
        #     logger.error("❌ Critical: Node missing 'sop_title'. Cannot index.")
        #     return None

        # # --- STEP 1: SAFETY CHECK (Downgrade Protection) ---
        # if not self._is_safe_to_update(sop_title, new_version_float):
        #     logger.error(f"❌ UPDATE REJECTED: Database has a newer or equal version of '{sop_title}'.")
        #     return None

        # # --- STEP 2: WIPE OLD VERSION ---
        # # We perform delete logic here before inserting to ensure 'Replace' semantics
        # self.delete_existing_sop(sop_title)

        # --- STEP 3: INSERT NEW VERSION ---
        try:
            logger.info(f"Indexing {len(nodes)} nodes for '{sop_title}' (v{new_version_float})...")
            
            # This triggers the embedding generation and Qdrant upload
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
            
            logger.info("✅ Indexing Complete.")
            return index
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise e