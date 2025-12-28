import sys
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

# --- Qdrant Imports for Filtering ---
from qdrant_client.http import models

# Add the project root to sys.path so Python can find 'src'
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# IMPORTS
try:
    from src.ingestion import IngestionPipeline
    from src.indexing import IndexingPipeline
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# =================================================================================================

def file_already_indexed(qdrant_manager, filename: str) -> bool:
    """
    Checks Qdrant to see if chunks from this filename already exist.
    Essential for resuming a large batch job (7000+ files) without duplicates.
    """
    try:
        # Create a filter to check if any point has "file_name" == filename
        filter_condition = models.Filter(
            must=[
                models.FieldCondition(
                    key="file_name", 
                    match=models.MatchValue(value=filename)
                )
            ]
        )
        
        # We only need 1 result to confirm existence
        res = qdrant_manager.client.scroll(
            collection_name=qdrant_manager.collection_name,
            scroll_filter=filter_condition,
            limit=1
        )
        return len(res[0]) > 0

    except Exception as e:
        return False


def save_nodes_to_file(nodes, output_dir: Path, original_filename: str):
    """
    Saves the extracted nodes to a text file for inspection.
    Format: Metadata -> Text -> Separator
    """
    # Create output filename (e.g., 'document.pdf' -> 'document.txt')
    txt_filename = Path(original_filename).with_suffix('.txt').name
    output_path = output_dir / txt_filename

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for i, node in enumerate(nodes):
                # Header for the chunk
                f.write(f"=== CHUNK {i+1} ===\n")
                
                # 1. Metadata (excluding the massive original text string to keep this section clean)
                # We create a copy to avoid modifying the actual node metadata in memory
                meta_display = node.metadata.copy()
                if "original_text" in meta_display:
                    del meta_display["original_text"]
                f.write(f"[METADATA]: {meta_display}\n\n")
                
                # 2. Lowercase Content (Used for Vector Search)
                f.write(f"[CONTENT - LOWERCASE]:\n{node.get_content()}\n\n")
                
                # 3. Original Content (Used for LLM Answer)
                original_text = node.metadata.get("original_text", "N/A")
                f.write(f"[CONTENT - ORIGINAL]:\n{original_text}\n")
                
                # 4. Separator
                f.write("\n" + "="*50 + "\n\n")
                
        print(f"   Saved text dump to: {txt_filename}")
    except Exception as e:
        print(f"   Failed to save text dump: {e}")



def main():
    """
    FASA Batch Processor - Robust ingestion.
    """
    start_time = time.time()
    
    # --- [NEW] Define and Create the Output Directory ---
    raw_dir = project_root / "data" / "raw_sops"
    processed_dir = project_root / "data" / "processed_txt" # <--- NEW
    processed_dir.mkdir(parents=True, exist_ok=True)        # <--- NEW

    if not raw_dir.exists():
        print(f"Directory not found: {raw_dir}")
        return

    supported_extensions = ['.pdf', '.docx', '.doc', '.docm']
    all_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in supported_extensions and f.is_file()]
    
    if not all_files:
        print(f"No supported files found in {raw_dir}")
        return

    print(f"##################    STARTING BULK INGESTION")
    print(f"##################    Target Directory: {raw_dir}")
    print(f"##################    Text Output Dir:  {processed_dir}") # <--- NEW
    print(f"##################    File Count: {len(all_files)}")
    print("="*100)

    # INITIALIZE PIPELINES
    try:
        ingest_pipe = IngestionPipeline()
        index_pipe = IndexingPipeline() 
        db_manager = index_pipe.db_manager
    except Exception as e:
        print(f"Failed to initialize pipelines: {e}")
        return
    
    # COUNTERS
    success_count = 0
    skipped_count = 0
    failed_files = []

    # --- PROCESS LOOP ---
    for i, file_path in enumerate(all_files, 1):
        filename = file_path.name
        
        # Progress Indicator
        print(f"[{i}/{len(all_files)}] Checking: {filename} ...", end=" ", flush=True)

        try:
            if file_already_indexed(db_manager, filename):
                print("EXISTS (Skipping)")
                skipped_count += 1
                continue

            # 2. INGESTION (Load -> Clean -> Chunk)
            print(">>>>>>>>>>>>>>>>>>>    Processing ...", end=" ", flush=True)
            nodes = ingest_pipe.run(str(file_path))

            if not nodes:
                print("EMPTY CONTENT")
                print(f"Skipping {filename}: No nodes generated.")
                failed_files.append(f"{filename} (Empty)")
                continue

            # --- [NEW] SAVE TO TEXT FILE HERE ---
            # We do this immediately after getting nodes, before indexing.
            save_nodes_to_file(nodes, processed_dir, filename) 
            # ------------------------------------

            result_index = index_pipe.run(nodes)
            
            if result_index:
                success_count += 1
                print(f"DONE ({len(nodes)} chunks)")
                print(f"Indexed: {filename}")
            else:
                print("DB FAIL")
                failed_files.append(f"{filename} (DB Error)")

        except Exception as e:
            print(f"CRASH: {e}")
            print(f"Failed processing {filename}: {e}")
            failed_files.append(f"{filename} (Error: {str(e)})")
        print("="*80)



if __name__ == "__main__":
    main()








# import sys
# from pathlib import Path
# from dotenv import load_dotenv
# import time

# load_dotenv()

# # --- Qdrant Imports for Filtering ---
# from qdrant_client.http import models

# # Add the project root to sys.path so Python can find 'src'
# project_root = Path(__file__).resolve().parent.parent
# sys.path.append(str(project_root))

# # IMPORTS
# try:
#     from src.ingestion import IngestionPipeline
#     from src.indexing import IndexingPipeline
# except ImportError as e:
#     print(f"Import Error: {e}")
#     sys.exit(1)

# # =================================================================================================

# def file_already_indexed(qdrant_manager, filename: str) -> bool:
#     """
#     Checks Qdrant to see if chunks from this filename already exist.
#     Essential for resuming a large batch job (7000+ files) without duplicates.
#     """
#     try:
#         # Create a filter to check if any point has "file_name" == filename
#         filter_condition = models.Filter(
#             must=[
#                 models.FieldCondition(
#                     key="file_name", 
#                     match=models.MatchValue(value=filename)
#                 )
#             ]
#         )
        
#         # We only need 1 result to confirm existence
#         res = qdrant_manager.client.scroll(
#             collection_name=qdrant_manager.collection_name,
#             scroll_filter=filter_condition,
#             limit=1
#         )
#         return len(res[0]) > 0

#     except Exception as e:
#         return False


# def save_nodes_to_file(nodes, output_dir: Path, original_filename: str):
#     """
#     Saves the extracted nodes to a text file for inspection.
#     Format: Metadata -> Text -> Separator
#     """
#     # Create output filename (e.g., 'document.pdf' -> 'document.txt')
#     txt_filename = Path(original_filename).with_suffix('.txt').name
#     output_path = output_dir / txt_filename

#     try:
#         with open(output_path, "w", encoding="utf-8") as f:
#             for i, node in enumerate(nodes):
#                 # Header for the chunk
#                 f.write(f"=== CHUNK {i+1} ===\n")
                
#                 # 1. Metadata
#                 f.write(f"[METADATA]: {node.metadata}\n\n")
                
#                 # 2. Text Content
#                 f.write(f"[CONTENT]:\n{node.get_content()}\n")
                
#                 # 3. Separator
#                 f.write("\n" + "-"*50 + "\n\n")
                
#         print(f"   Saved text dump to: {txt_filename}")
#     except Exception as e:
#         print(f"   Failed to save text dump: {e}")



# def main():
#     """
#     FASA Batch Processor - Robust ingestion.
#     """
#     start_time = time.time()
    
#     # --- [NEW] Define and Create the Output Directory ---
#     raw_dir = project_root / "data" / "raw_sops"
#     processed_dir = project_root / "data" / "processed_txt" # <--- NEW
#     processed_dir.mkdir(parents=True, exist_ok=True)        # <--- NEW

#     if not raw_dir.exists():
#         print(f"Directory not found: {raw_dir}")
#         return

#     supported_extensions = ['.pdf', '.docx', '.doc', '.docm']
#     all_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in supported_extensions and f.is_file()]
    
#     if not all_files:
#         print(f"No supported files found in {raw_dir}")
#         return

#     print(f"##################    STARTING BULK INGESTION")
#     print(f"##################    Target Directory: {raw_dir}")
#     print(f"##################    Text Output Dir:  {processed_dir}") # <--- NEW
#     print(f"##################    File Count: {len(all_files)}")
#     print("="*100)

#     # INITIALIZE PIPELINES
#     try:
#         ingest_pipe = IngestionPipeline()
#         index_pipe = IndexingPipeline() 
#         db_manager = index_pipe.db_manager
#     except Exception as e:
#         print(f"Failed to initialize pipelines: {e}")
#         return
    
#     # COUNTERS
#     success_count = 0
#     skipped_count = 0
#     failed_files = []

#     # --- PROCESS LOOP ---
#     for i, file_path in enumerate(all_files, 1):
#         filename = file_path.name
        
#         # Progress Indicator
#         print(f"[{i}/{len(all_files)}] Checking: {filename} ...", end=" ", flush=True)

#         try:
#             if file_already_indexed(db_manager, filename):
#                 print("EXISTS (Skipping)")
#                 skipped_count += 1
#                 continue

#             # 2. INGESTION (Load -> Clean -> Chunk)
#             print(">>>>>>>>>>>>>>>>>>>    Processing ...", end=" ", flush=True)
#             nodes = ingest_pipe.run(str(file_path))

#             if not nodes:
#                 print("EMPTY CONTENT")
#                 print(f"Skipping {filename}: No nodes generated.")
#                 failed_files.append(f"{filename} (Empty)")
#                 continue

#             # --- [NEW] SAVE TO TEXT FILE HERE ---
#             # We do this immediately after getting nodes, before indexing.
#             save_nodes_to_file(nodes, processed_dir, filename) 
#             # ------------------------------------

#             result_index = index_pipe.run(nodes)
            
#             if result_index:
#                 success_count += 1
#                 print(f"DONE ({len(nodes)} chunks)")
#                 print(f"Indexed: {filename}")
#             else:
#                 print("DB FAIL")
#                 failed_files.append(f"{filename} (DB Error)")

#         except Exception as e:
#             print(f"CRASH: {e}")
#             print(f"Failed processing {filename}: {e}")
#             failed_files.append(f"{filename} (Error: {str(e)})")
#         print("="*80)






    
# if __name__ == "__main__":
#     main()