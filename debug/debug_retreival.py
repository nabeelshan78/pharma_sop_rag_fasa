import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import time

# --- Setup Project Path ---
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

load_dotenv()

# --- Imports ---
from llama_index.core import VectorStoreIndex
# <--- ADDED IMPORT --->
from llama_index.core.postprocessor import SimilarityPostprocessor 
from src.indexing.vector_db import QdrantManager
from src.indexing.embeddings import EmbeddingManager

# =============================================================================

def save_retrieval_dump(nodes, query_text, output_file="retrieval_dump.txt"):
    """
    Writes the raw retrieved nodes AND the simulated LLM context to a file.
    Captures both Lowercase (Search) and Original (Display) text.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        # --- PART 1: HEADER ---
        f.write(f"==========================================================\n")
        f.write(f"QUERY: {query_text}\n")
        f.write(f"TOTAL CHUNKS FOUND: {len(nodes)}\n")
        f.write(f"==========================================================\n\n")

        llm_context_accumulated = ""

        for i, node_with_score in enumerate(nodes, 1):
            score = node_with_score.score
            node = node_with_score.node
            meta = node.metadata
            
            content = node.get_content() 

            # Accumulate the ORIGINAL text for the "Simulated View" 
            llm_context_accumulated += f"{content}\n\n"
            
            # --- WRITE CHUNK DETAILS ---
            f.write(f"--- RANK #{i} (Score: {score:.4f}) ---\n")
            f.write(f"[FILE]: {meta.get('file_name', 'Unknown')}\n")
            f.write(f"[PAGE]: {meta.get('page_label', 'Unknown')}\n")
            f.write(f"[SOP TITLE]: {meta.get('sop_title', 'Unknown')}\n")
            
            # f.write(f"\n[CONTENT - LOWERCASE (Vector View)]:\n{content_lower}\n")
            f.write(f"\n[CONTENT - ORIGINAL (LLM View)]:\n{content}\n")
            
            f.write("\n" + "="*60 + "\n\n")
            
    print(f"✅ Dump saved to: {output_file}")

def run_debug():
    print("--- FASA RETRIEVAL DEBUGGER ---")
    
    # 1. Initialize Embeddings
    try:
        EmbeddingManager.configure_global_settings()
    except Exception as e:
        print(f"❌ Failed to load embeddings: {e}")
        return

    # 2. Connect to Qdrant
    try:
        db_manager = QdrantManager()
        index = VectorStoreIndex.from_vector_store(vector_store=db_manager.vector_store)
        print("✅ Connected to Qdrant Index.")
    except Exception as e:
        print(f"❌ Failed to connect to DB: {e}")
        return

    # 3. Create Retriever (Hybrid Mode)
    retriever = index.as_retriever(
        similarity_top_k=7, 
        vector_store_query_mode="hybrid", 
        alpha=0.7 
    )
    
    # 4. Loop
    while True:
        print("\n" + "="*40)
        query = input("Enter Query (or 'q' to quit): ").strip()
        
        if query.lower() == 'q':
            break
        if not query:
            continue

        print(f"🔍 Searching for: '{query}'...")
        
        try:
            # A. EXECUTE RAW RETRIEVAL
            raw_nodes = retriever.retrieve(query)
            print(f"   > Raw Results: Found {len(raw_nodes)} candidates.")
            
            filename = f"debug_retrieval_{int(time.time())}.txt"
            save_retrieval_dump(raw_nodes, query, filename)
            

        except Exception as e:
            print(f"❌ Error during retrieval: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_debug()