# import sys
# import os
# import json
# from dotenv import load_dotenv

# # 1. Load Environment & Paths
# load_dotenv()
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from src.config import settings
# from src.core.logger import setup_logger
# from src.indexing.vector_db import QdrantManager
# from src.rag import RAGRetriever

# logger = setup_logger("DEBUGGER")

# def run_diagnostics():
#     logger.info("🕵️  Starting System Diagnostics...")

#     # --- STEP 1: CHECK DATABASE HEALTH ---
#     logger.info("--- [Step 1] Checking Vector Database ---")
    
#     try:
#         qdrant = QdrantManager()
#         collection_info = qdrant.client.get_collection(settings.COLLECTION_NAME)
#         count = collection_info.points_count
        
#         if count == 0:
#             logger.error("❌ Database is EMPTY! Bulk Ingest failed to persist data.")
#             return
            
#         logger.info(f"✅ Connection Successful")
#         logger.info(f"📊 Total Chunks Stored: {count}")
        
#     except Exception as e:
#         logger.critical(f"🔥 Database Connection Failed: {e}")
#         return

#     # --- STEP 2: PEEK AT DATA ---
#     logger.info("\n--- [Step 2] Inspecting Metadata (First Chunk) ---")
    
#     # Scroll to get 1 record
#     records, _ = qdrant.client.scroll(
#         collection_name=settings.COLLECTION_NAME,
#         limit=1,
#         with_payload=True
#     )
    
#     if records:
#         payload = records[0].payload
#         logger.info(f"📄 SOP Name: {payload.get('sop_name')}")
#         logger.info(f"🔖 Version:  {payload.get('version')}")
        
#         # --- LOGIC TO FIND TEXT ---
#         # LlamaIndex stores text differently depending on version
#         # 1. Check direct 'text' field
#         text_preview = payload.get('text')
        
#         # 2. Check '_node_content' (JSON string)
#         if not text_preview and '_node_content' in payload:
#             try:
#                 node_content = json.loads(payload['_node_content'])
#                 text_preview = node_content.get('text', '')
#             except:
#                 text_preview = "Error parsing _node_content"

#         if text_preview:
#             logger.info(f"📝 Text Preview: {text_preview}...")
#         else:
#             logger.warning(f"⚠️ Raw Keys Found: {list(payload.keys())}")
#     else:
#         logger.warning("⚠️ Could not retrieve records.")

#     # --- STEP 3: TEST RAG RETRIEVAL ---
#     logger.info("\n--- [Step 3] Simulation: Asking a Question ---")
    
#     try:
#         rag = RAGRetriever()
        
#         query = "Who is Nabeel?"
#         logger.info(f"❓ Query: {query}")
        
#         result = rag.query(query)
        
#         print("\n" + "="*50)
#         print(f"🤖 AI Answer:\n{result['answer']}")
#         print("-" * 50)
        
#         if result['sources']:
#             print("📚 CITATIONS FOUND:")
#             for source in result['sources']:
#                 print(f"   - {source['sop_name']} (v{source['version']}) | Score: {source['score']}")
#         else:
#             print("⚠️ No sources found (Check your similarity threshold)")
#         print("="*50 + "\n")
        
#     except Exception as e:
#         logger.error(f"❌ Simulation Failed: {e}")

# if __name__ == "__main__":
#     run_diagnostics()




# Create a file named test_import.py
try:
    from fastembed import TextEmbedding
    print("✅ FastEmbed imported successfully!")
except ImportError as e:
    print(f"❌ Failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")