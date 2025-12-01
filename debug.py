import sys
import os
import json
import random
from dotenv import load_dotenv

# 1. Load Environment & Paths
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.core.logger import setup_logger
from src.indexing.vector_db import QdrantManager

logger = setup_logger("DEBUGGER")

def inspect_random_chunks():
    logger.info("🕵️  Starting Deep Inspection...")

    # --- STEP 1: CONNECT ---
    try:
        qdrant = QdrantManager()
        collection_info = qdrant.client.get_collection(settings.COLLECTION_NAME)
        count = collection_info.points_count
        logger.info(f"📊 Total Chunks in DB: {count}")
        
        if count == 0:
            logger.error("❌ Database is EMPTY!")
            return
    except Exception as e:
        logger.critical(f"🔥 Database Connection Failed: {e}")
        return

    # --- STEP 2: FETCH & RANDOMIZE ---
    logger.info("🎲 Fetching random sample to inspect content quality...")
    
    # We fetch up to 100 chunks to get a good variety
    records, _ = qdrant.client.scroll(
        collection_name=settings.COLLECTION_NAME,
        limit=100,
        with_payload=True
    )
    
    if not records:
        logger.warning("⚠️ Could not retrieve records.")
        return

    # Pick 5 random records from the batch
    sample_size = min(len(records), 5)
    random_records = random.sample(records, sample_size)

    print("\n" + "!" * 50)
    print(f"DISPLAYING {sample_size} RANDOM CHUNKS FROM DATABASE")
    print("!" * 50 + "\n")

    # --- STEP 3: PRINT FULL CONTENT ---
    for i, record in enumerate(random_records):
        payload = record.payload
        sop_name = payload.get('sop_name', 'Unknown')
        version = payload.get('version', 'Unknown')
        
        # --- TEXT EXTRACTION LOGIC ---
        full_text = "NO TEXT FOUND"
        
        # Strategy 1: Direct Text
        if payload.get('text'):
            full_text = payload.get('text')
            
        # Strategy 2: LlamaIndex Node Content (JSON)
        elif '_node_content' in payload:
            try:
                # LlamaIndex stores the text inside a JSON string here
                content_json = json.loads(payload['_node_content'])
                full_text = content_json.get('text', 'No text key in JSON')
            except:
                full_text = "Error parsing _node_content JSON"

        # --- THE OUTPUT ---
        print(f"CHUNK #{i+1} | Source: {sop_name} (v{version})")
        print("-" * 20)
        print(full_text)
        print("\n" + "=" * 50 + "\n")

if __name__ == "__main__":
    inspect_random_chunks()