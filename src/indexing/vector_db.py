import os
from typing import List, Optional

# --- LlamaIndex Imports ---
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

# --- Qdrant Native Imports ---
from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, Distance, SparseVectorParams
from qdrant_client.http import models as rest_models  # Needed for Filters

# =================================================================================================

class QdrantManager:
    """
    Manages Qdrant Vector Database interactions.
    """

    def __init__(self, collection_name: str = "fasa_sops"):        
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.collection_name = collection_name
        
        # Nomic-embed-text is 768 dimensions
        self.vector_dim = 768 

        # Initialize Native Client
        self.client = QdrantClient(
            url=self.url, 
            timeout=30.0 
        )
        
        # Check/Create Collection
        self.ensure_collection_exists()
        
        # Initialize LlamaIndex Store
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            batch_size=2, # Ollama can handle slightly larger batches locally
            enable_hybrid=True,
            fastembed_sparse_model="Qdrant/bm25",
            dense_vector_name="text-dense",
            sparse_vector_name="text-sparse"
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)


    def ensure_collection_exists(self):
        """
        Creates the collection if it doesn't exist.
        """
        if not self.client.collection_exists(self.collection_name):
            print(f"Collection '{self.collection_name}' not found. Creating...")
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "text-dense": VectorParams(
                            size=self.vector_dim,
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "text-sparse": SparseVectorParams()
                    }
                )
                print(f"Collection '{self.collection_name}' created successfully.")
            except Exception as e:
                print(f"Failed to create collection '{self.collection_name}': {e}")
                raise e
        else:
            # Simple validation to ensure we aren't writing to a mismatching schema
            info = self.client.get_collection(self.collection_name)
            dense_params = info.config.params.vectors.get("text-dense")
            if not dense_params or dense_params.size != self.vector_dim:
                print(f"Collection exists but has wrong dimensions! Expected {self.vector_dim}")
                raise ValueError("Dimension mismatch in Qdrant. Please delete the collection and restart.")


    
    # --- UPDATED: HELPER TO UPDATE STATUS IN DB ---
    def _set_db_status_inactive(self, doc_num: str, title: str):
        """
        Forcefully updates existing chunks to 'Inactive' based on Doc Number + Title.
        """
        print(f"📉 Marking older version of '{doc_num} - {title}' as Inactive in DB...")
        
        # We need to match BOTH Document Number AND Title
        self.client.set_payload(
            collection_name=self.collection_name,
            payload={"status": "Inactive"},
            filter=rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="document_number",
                        match=rest_models.MatchValue(value=doc_num)
                    ),
                    rest_models.FieldCondition(
                        key="sop_title",
                        match=rest_models.MatchValue(value=title)
                    )
                ]
            )
        )

    # # --- NEW: HELPER TO UPDATE STATUS IN DB ---
    # def _set_db_status_inactive(self, file_name: str):
    #     """
    #     Forcefully updates ALL existing chunks of a file to 'Inactive' in Qdrant.
    #     """
    #     print(f"📉 Marking older version of '{file_name}' as Inactive in DB...")
    #     self.client.set_payload(
    #         collection_name=self.collection_name,
    #         payload={"status": "Inactive"},
    #         filter=rest_models.Filter(
    #             must=[
    #                 rest_models.FieldCondition(
    #                     key="file_name",
    #                     match=rest_models.MatchValue(value=file_name)
    #                 )
    #             ]
    #         )
    #     )

    # --- NEW: VERSION LOGIC ---
    # --- UPDATED: VERSION LOGIC ---
    def _resolve_version_status(self, doc_num: str, title: str, incoming_version: float) -> str:
        """
        Decides if NEW nodes should be 'Active' based on Doc Number + Title comparison.
        """
        # 1. Find currently ACTIVE chunks for this specific DocNum + Title
        scroll_filter = rest_models.Filter(
            must=[
                rest_models.FieldCondition(key="document_number", match=rest_models.MatchValue(value=doc_num)),
                rest_models.FieldCondition(key="sop_title", match=rest_models.MatchValue(value=title)),
                rest_models.FieldCondition(key="status", match=rest_models.MatchValue(value="Active"))
            ]
        )
        
        # Check if an active version exists
        res = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=scroll_filter,
            limit=1,
            with_payload=True
        )
        points, _ = res

        # Case 1: No active version exists.
        if not points:
            return "Active"

        # Case 2: Active version found. Compare versions.
        existing_payload = points[0].payload
        existing_version = float(existing_payload.get("version_number", 0.0))

        print(f"⚔️ Version Clash for {doc_num}: Incoming v{incoming_version} vs Existing v{existing_version}")

        if incoming_version > existing_version:
            # WINNER: New one is newer. 
            self._set_db_status_inactive(doc_num, title)
            return "Active"
        
        elif incoming_version < existing_version:
            # LOSER: New one is older.
            print(f"⚠️ Incoming {doc_num} is older (v{incoming_version}) than Active (v{existing_version}). Marking Inactive.")
            return "Inactive"
            
        else:
            # TIE: Same version. Overwrite/Active.
            return "Active"


    # def _resolve_version_status(self, file_name: str, incoming_version: float) -> str:
    #     """
    #     Decides if the NEW nodes should be 'Active' or 'Inactive'.
    #     Side Effect: Deactivates old nodes in DB if new one is winner.
    #     """
    #     # 1. Find currently ACTIVE chunks for this file
    #     scroll_filter = rest_models.Filter(
    #         must=[
    #             rest_models.FieldCondition(key="file_name", match=rest_models.MatchValue(value=file_name)),
    #             rest_models.FieldCondition(key="status", match=rest_models.MatchValue(value="Active"))
    #         ]
    #     )
        
    #     # We only need 1 point to check the version
    #     res = self.client.scroll(
    #         collection_name=self.collection_name,
    #         scroll_filter=scroll_filter,
    #         limit=1,
    #         with_payload=True
    #     )
    #     points, _ = res

    #     # Case 1: No active version exists. (First upload or all previous are inactive)
    #     if not points:
    #         return "Active"

    #     # Case 2: Active version found. Let's compare.
    #     existing_payload = points[0].payload
    #     existing_version = float(existing_payload.get("version_number", 0.0))

    #     print(f"⚔️ Version Clash: Incoming v{incoming_version} vs Existing v{existing_version}")

    #     if incoming_version > existing_version:
    #         # WINNER: New one is newer. 
    #         # Action: Kill the old one, let new one be Active.
    #         self._set_db_status_inactive(file_name)
    #         return "Active"
        
    #     elif incoming_version < existing_version:
    #         # LOSER: New one is actually an old backup.
    #         # Action: Keep old one alive, mark this arrival as Inactive.
    #         print("⚠️ Incoming file is older than current Active. Marking incoming as Inactive.")
    #         return "Inactive"
            
    #     else:
    #         # TIE: Same version. 
    #         # Usually we treat this as a "Re-upload". We keep it Active and overwrite effectively.
    #         return "Active"
        



    # --- UPDATED: INSERT METHOD ---
    def insert_nodes(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
        if not nodes:
            return None

        # 1. Extract Metadata from first node
        first_node = nodes[0]
        
        # --- CHANGED: Get Doc Num and Title instead of Filename ---
        doc_num = first_node.metadata.get("document_number")
        sop_title = first_node.metadata.get("sop_title", "Unknown Title")
        
        # Parse version
        try:
            raw_ver = first_node.metadata.get("version_number", 1.0)
            incoming_version = float(raw_ver)
        except:
            incoming_version = 1.0

        # 2. DETERMINE STATUS
        # Only run check if we actually have a Document Number to check against
        if doc_num:
            determined_status = self._resolve_version_status(doc_num, sop_title, incoming_version)
        else:
            # Fallback if metadata extraction failed (e.g. poor PDF parsing)
            print("⚠️ No Document Number found in metadata. Defaulting to Active.")
            determined_status = "Active"

        # 3. APPLY STATUS TO ALL INCOMING NODES
        for node in nodes:
            node.metadata["status"] = determined_status

        # 4. INSERT
        try:
            print(f">>> Indexing {len(nodes)} nodes for '{doc_num}: {sop_title}' as '{determined_status}'...")
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
            print(">>> Indexing Complete.")
            return index
            
        except Exception as e:
            print(f"Indexing failed: {e}")
            raise e
        

    # # --- UPDATED INSERT METHOD ---
    # def insert_nodes(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
    #     if not nodes:
    #         return None

    #     # 1. Extract Metadata from first node
    #     first_node = nodes[0]
    #     file_name = first_node.metadata.get("file_name")
    #     sop_title = first_node.metadata.get("sop_title", "Unknown")
        
    #     # Parse version (Handle string/float safety)
    #     try:
    #         raw_ver = first_node.metadata.get("version_number", 1.0)
    #         incoming_version = float(raw_ver)
    #     except:
    #         incoming_version = 1.0

    #     # 2. DETERMINE STATUS (The Magic Step)
    #     if file_name:
    #         determined_status = self._resolve_version_status(file_name, incoming_version)
    #     else:
    #         determined_status = "Active" # Fallback if no filename

    #     # 3. APPLY STATUS TO ALL INCOMING NODES
    #     # We modify the nodes list *before* it goes into the index
    #     for node in nodes:
    #         node.metadata["status"] = determined_status

    #     # 4. INSERT
    #     try:
    #         print(f">>> Indexing {len(nodes)} nodes for '{sop_title}' as '{determined_status}'...")
    #         index = VectorStoreIndex(
    #             nodes, 
    #             storage_context=self.storage_context
    #         )
    #         print(">>> Indexing Complete.")
    #         return index
            
    #     except Exception as e:
    #         print(f"Indexing failed: {e}")
    #         raise e

    # def insert_nodes(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
    #     """
    #     Main Ingestion Entry Point.
    #     """
    #     if not nodes:
    #         return None

    #     first_node = nodes[0]
    #     sop_title = first_node.metadata.get("sop_title", "Unknown")
        
    #     # --- INSERT ---
    #     try:
    #         print(f">>>>>>>>>>>>>>>>>      Indexing {len(nodes)} nodes for '{sop_title}'...")
    #         index = VectorStoreIndex(
    #             nodes, 
    #             storage_context=self.storage_context
    #         )
    #         print(">>>>>>>>>>>>>>>>>>      Indexing Complete.")
    #         return index
            
    #     except Exception as e:
    #         print(f"Indexing failed: {e}")
    #         raise e