# import sys
# import os
# import json
# import random
# from dotenv import load_dotenv

# # 1. Load Environment & Paths
# load_dotenv()
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from src.config import settings
# from src.core.logger import setup_logger
# from src.indexing.vector_db import QdrantManager

# logger = setup_logger("DEBUGGER")

# def inspect_random_chunks():
#     logger.info("🕵️  Starting Deep Inspection...")

#     # --- STEP 1: CONNECT ---
#     try:
#         qdrant = QdrantManager()
#         collection_info = qdrant.client.get_collection(settings.COLLECTION_NAME)
#         count = collection_info.points_count
#         logger.info(f"📊 Total Chunks in DB: {count}")
        
#         if count == 0:
#             logger.error("❌ Database is EMPTY!")
#             return
#     except Exception as e:
#         logger.critical(f"🔥 Database Connection Failed: {e}")
#         return

#     # --- STEP 2: FETCH & RANDOMIZE ---
#     logger.info("🎲 Fetching random sample to inspect content quality...")
    
#     # We fetch up to 100 chunks to get a good variety
#     records, _ = qdrant.client.scroll(
#         collection_name=settings.COLLECTION_NAME,
#         limit=100,
#         with_payload=True
#     )
    
#     if not records:
#         logger.warning("⚠️ Could not retrieve records.")
#         return

#     # Pick 5 random records from the batch
#     sample_size = min(len(records), 5)
#     random_records = random.sample(records, sample_size)

#     print("\n" + "!" * 50)
#     print(f"DISPLAYING {sample_size} RANDOM CHUNKS FROM DATABASE")
#     print("!" * 50 + "\n")

#     # --- STEP 3: PRINT FULL CONTENT ---
#     for i, record in enumerate(random_records):
#         payload = record.payload
#         sop_name = payload.get('sop_name', 'Unknown')
#         version = payload.get('version', 'Unknown')
        
#         # --- TEXT EXTRACTION LOGIC ---
#         full_text = "NO TEXT FOUND"
        
#         # Strategy 1: Direct Text
#         if payload.get('text'):
#             full_text = payload.get('text')
            
#         # Strategy 2: LlamaIndex Node Content (JSON)
#         elif '_node_content' in payload:
#             try:
#                 # LlamaIndex stores the text inside a JSON string here
#                 content_json = json.loads(payload['_node_content'])
#                 full_text = content_json.get('text', 'No text key in JSON')
#             except:
#                 full_text = "Error parsing _node_content JSON"

#         # --- THE OUTPUT ---
#         print(f"CHUNK #{i+1} | Source: {sop_name} (v{version})")
#         print("-" * 20)
#         print(full_text)
#         print("\n" + "=" * 50 + "\n")

# if __name__ == "__main__":
#     inspect_random_chunks()






# from qdrant_client import QdrantClient, models
# from src.config import settings

# # Connect directly to Qdrant
# client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

# def debug_term(term):
#     print(f"\n🔎 HUNTING FOR EXACT TEXT: '{term}'")
    
#     # This asks Qdrant: "Show me ANY chunk that actually contains this word"
#     # It ignores vectors/relevance. It's a raw database lookup.
#     res = client.scroll(
#         collection_name=settings.COLLECTION_NAME,
#         scroll_filter=models.Filter(
#             must=[
#                 models.FieldCondition(
#                     key="text", # Check the actual content
#                     match=models.MatchText(text=term)
#                 )
#             ]
#         ),
#         limit=10,
#         with_payload=True
#     )
    
#     hits = res[0]
#     if not hits:
#         print("❌ CRITICAL: The text was NOT found in the database. Ingestion failed.")
#     else:
#         print(f"✅ Found {len(hits)} chunks containing the term.")
#         for hit in hits:
#             meta = hit.payload.get("metadata", {})
#             print(f"   - File: {meta.get('file_name')} | Page: {meta.get('page_label')}")
#             print(f"     Preview: {hit.payload.get('text', '')[:100]}...\n")

# if __name__ == "__main__":
#     # Test the specific term that is failing
#     debug_term("fulfilling a quality assurance function")





# import sys
# from pathlib import Path
# from qdrant_client import QdrantClient, models
# from dotenv import load_dotenv

# # Path Setup to find 'src'
# sys.path.append(str(Path(__file__).resolve().parent))
# from src.config import settings

# def inspect_database():
#     print("--- 🕵️ Qdrant Database Inspector ---")
    
#     # 1. Connect
#     try:
#         client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
#         count = client.count(collection_name=settings.COLLECTION_NAME).count
#         print(f"✅ Connected. Total Chunks in DB: {count}")
        
#         if count == 0:
#             print("❌ DATABASE IS EMPTY. Ingestion did not work.")
#             return
#     except Exception as e:
#         print(f"❌ Connection Failed: {e}")
#         return

#     # 2. List ALL Filenames present in DB
#     print("\n--- 📂 Files Currently Indexed ---")
    
#     # We scroll through the DB to find unique filenames
#     # (Qdrant doesn't have a 'SELECT DISTINCT' so we scan)
#     unique_files = set()
#     next_offset = None
    
#     while True:
#         records, next_offset = client.scroll(
#             collection_name=settings.COLLECTION_NAME,
#             limit=100,
#             offset=next_offset,
#             with_payload=True,
#             with_vectors=False
#         )
        
#         for record in records:
#             # check all keys in metadata
#             meta = record.payload.get("metadata", {})
#             for key in meta.keys():
#                 if "file_name" in key:
#                     print(meta[key])
#             # # Check both 'file_name' and 'filename' just in case
#             # fname = record.payload.get("metadata", {}).get("file_name")
#             # print(fname)
#             # if fname:
#             #     unique_files.add(fname)
        
#         if next_offset is None:
#             break
            
#     if not unique_files:
#         print("⚠️ No filenames found in metadata. Did ingestion save metadata?")
#     else:
#         for f in sorted(unique_files):
#             print(f" - {f}")

#     # 3. Inspect Specific Target File
#     target_name = "GRT_PROC_English_stamped_Rev06.docmNov302025052119"
#     print(f"\n--- 🔎 Inspecting Target: {target_name} ---")
    
#     # Try to find it (Partial Match logic)
#     found_files = [f for f in unique_files if "GRT PROC" in f]
    
#     if not found_files:
#         print(f"❌ CRITICAL: No file matching 'GRT_PROC' exists in the database.")
#         print("POSSIBLE CAUSE: The 'bulk_ingest.py' script skipped it because the extension was '.docmNov...' instead of '.docx'.")
#         return

#     print(f"Found matches in DB: {found_files}")
    
#     # Dump Content of the first match
#     match = found_files[0]
#     print(f"\n--- 📝 Content Dump for: {match} ---")
    
#     res = client.scroll(
#         collection_name=settings.COLLECTION_NAME,
#         scroll_filter=models.Filter(
#             must=[
#                 models.FieldCondition(
#                     key="file_name",
#                     match=models.MatchValue(value=match)
#                 )
#             ]
#         ),
#         limit=5  # Just show first 5 chunks
#     )
    
#     chunks = res[0]
#     for i, chunk in enumerate(chunks):
#         meta = chunk.payload.get("metadata", {})
#         text = chunk.payload.get("text", "")
#         print(f"\n[Chunk {i+1}] Page {meta.get('page_label')}")
#         print(f"Content Preview: {text[:200]}...")
#         print("-" * 30)

# if __name__ == "__main__":
#     inspect_database()





import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Path Setup
sys.path.append(str(Path(__file__).resolve().parent))
load_dotenv()

# Import your RAG Engine
from src.rag import FASAEngine

# Setup Logging to console only
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def x_ray_query(question):
    print(f"\n⚡ X-RAY QUERY: '{question}'")
    print("=" * 60)
    
    try:
        engine = FASAEngine()
        # We access the internal query engine to get raw nodes
        response = engine.query_engine.query(question)
        
        if not response.source_nodes:
            print("❌ NO CHUNKS FOUND. The retriever found nothing.")
            return

        print(f"✅ FOUND {len(response.source_nodes)} CHUNKS.")
        
        # PRINT THE TOP 3 CHUNKS
        for i, node_score in enumerate(response.source_nodes[:3]):
            score = node_score.score
            meta = node_score.node.metadata
            text = node_score.node.text
            
            print(f"\n[RANK #{i+1}] Score: {score:.3f}")
            print(f"File: {meta.get('file_name')} | Page: {meta.get('page_label')}")
            print("-" * 30)
            # Print the text so we can see if it's just a Table of Contents
            print(text.strip()[:500]) 
            print("-" * 30)
            
        print(f"\n🤖 AI RESPONSE:\n{response}")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    # Test the exact failing question
    x_ray_query("What are the responsibilities of CAPA Initiator?")