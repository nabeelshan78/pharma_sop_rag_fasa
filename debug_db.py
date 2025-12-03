import sys
import os
import random
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("QdrantDebugger")

# Configuration
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "fasa_sops_llama"
VECTOR_DIM = 768  # Google Gemini Dimension

def get_random_dense_vector(dim: int) -> List[float]:
    """Generates a random dense vector (simulating Gemini)."""
    return [random.random() for _ in range(dim)]

def get_random_sparse_vector() -> models.SparseVector:
    """Generates a random sparse vector (simulating BM25)."""
    # Simulates finding 3 keywords in a vocab of 1000 words
    indices = random.sample(range(0, 1000), 3)
    values = [random.random() for _ in range(3)]
    return models.SparseVector(indices=indices, values=values)

def diagnose_qdrant():
    logger.info("--- 🕵️ Qdrant Diagnostic Tool ---")

    # 1. Check Connection
    try:
        client = QdrantClient(url=QDRANT_URL)
        logger.info(f"✅ Connection successful to {QDRANT_URL}")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return

    # 2. Check Collection Existence
    if not client.collection_exists(COLLECTION_NAME):
        logger.error(f"❌ Collection '{COLLECTION_NAME}' DOES NOT EXIST.")
        logger.info("👉 Fix: Run your 'src/indexing/vector_db.py' code (ensure create_collection is called).")
        return
    else:
        logger.info(f"✅ Collection '{COLLECTION_NAME}' found.")

    # 3. Inspect Schema (The Critical Part)
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        config = collection_info.config
        
        # Check Dense
        if "text-dense" in config.params.vectors:
            logger.info("✅ Dense Vector Config ('text-dense') detected.")
        else:
            logger.error("❌ MISSING 'text-dense' configuration.")

        # Check Sparse
        if config.params.sparse_vectors and "text-sparse" in config.params.sparse_vectors:
            logger.info("✅ Sparse Vector Config ('text-sparse') detected.")
        else:
            logger.error("❌ MISSING 'text-sparse' configuration. This causes the 'Not existing vector name' error.")
            return # Cannot proceed with test if schema is wrong

    except Exception as e:
        logger.error(f"❌ Failed to inspect schema: {e}")
        return

    # 4. Test Insertion (Write)
    logger.info("--- 🧪 Testing Write Operation ---")
    try:
        # Create a dummy point with BOTH vector types
        dummy_id = 999999999 # High ID to distinguish from real data
        
        point = models.PointStruct(
            id=dummy_id,
            vector={
                "text-dense": get_random_dense_vector(VECTOR_DIM),
                "text-sparse": get_random_sparse_vector(),
            },
            payload={
                "text": "This is a DUMMY DEBUG chunk.",
                "sop_title": "DEBUG_SOP",
                "page_label": "0"
            }
        )

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        logger.info("✅ Dummy chunk inserted successfully.")

    except Exception as e:
        logger.error(f"❌ Write Failed: {e}")
        return

    # 5. Test Retrieval (Read)
    logger.info("--- 🧪 Testing Read Operation ---")
    try:
        # Retrieve by ID
        results = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[dummy_id],
            with_vectors=True # Ask to see the vectors back
        )

        if results:
            retrieved_point = results[0]
            logger.info(f"✅ Retrieved Point ID: {retrieved_point.id}")
            
            # Verify Vector Payload presence
            has_dense = "text-dense" in retrieved_point.vector
            has_sparse = "text-sparse" in retrieved_point.vector
            
            if has_dense and has_sparse:
                logger.info("✅ BOTH vectors (Dense + Sparse) are present. Schema is perfect!")
            else:
                logger.warning(f"⚠️ Missing vectors in retrieval. Dense: {has_dense}, Sparse: {has_sparse}")
            
            # Clean up (Delete the dummy)
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(points=[dummy_id])
            )
            logger.info("🧹 Dummy chunk cleaned up.")
            
        else:
            logger.error("❌ Point was inserted but could not be retrieved.")

    except Exception as e:
        logger.error(f"❌ Read Failed: {e}")

if __name__ == "__main__":
    diagnose_qdrant()