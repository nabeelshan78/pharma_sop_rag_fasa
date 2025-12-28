import os
from typing import List, Optional

# --- LlamaIndex Imports ---
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore

# --- Qdrant Native Imports ---
from qdrant_client import QdrantClient, models
from qdrant_client.models import VectorParams, Distance, SparseVectorParams

# =================================================================================================

class QdrantManager:
    """
    Manages Qdrant Vector Database interactions.
    """

    def __init__(self, collection_name: str = "fasa_sops_ph1"):        
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

    def insert_nodes(self, nodes: List[TextNode]) -> Optional[VectorStoreIndex]:
        """
        Main Ingestion Entry Point.
        """
        if not nodes:
            return None

        first_node = nodes[0]
        sop_title = first_node.metadata.get("sop_title", "Unknown")
        
        # --- INSERT ---
        try:
            print(f">>>>>>>>>>>>>>>>>      Indexing {len(nodes)} nodes for '{sop_title}'...")
            index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context
            )
            print(">>>>>>>>>>>>>>>>>>      Indexing Complete.")
            return index
            
        except Exception as e:
            print(f"Indexing failed: {e}")
            raise e