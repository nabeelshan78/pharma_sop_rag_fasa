import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import time

# -----------------------------------------------------------------------------
# PATH SETUP (CRITICAL)
# -----------------------------------------------------------------------------
# Add the project root to sys.path so Python can find 'src'
# We assume this script is located in /scripts/ inside the root.
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Load Env Vars (API Keys)
load_dotenv()

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------
try:
    from src.core.logger import setup_logger
    from src.ingestion import IngestionPipeline
    from src.indexing import IndexingPipeline
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Current Path: {sys.path}")
    sys.exit(1)

# Setup Logger
logger = setup_logger("BULK_INGEST")

def main():
    """
    FASA Batch Processor.
    Scans data/raw_sops/, runs the Ingestion Pipeline, and Indexing Pipeline.
    """
    start_time = time.time()
    
    # 1. DEFINE PATHS
    # Using Pathlib for cross-OS compatibility (Windows/Linux)
    raw_dir = project_root / "data" / "raw_sops"
    
    if not raw_dir.exists():
        logger.error(f"❌ Directory not found: {raw_dir}")
        logger.info("Please create 'data/raw_sops' and place your SOP files there.")
        return

    # 2. SCAN FILES
    # We look for PDF, DOCX, DOC. 
    # Note: txt is excluded as SOPs are usually formal docs, but added if needed.
    supported_extensions = ['.pdf', '.docx', '.doc']
    files = [f for f in raw_dir.iterdir() if f.suffix.lower() in supported_extensions and f.is_file()]
    
    if not files:
        logger.warning(f"⚠️ No supported files found in {raw_dir}")
        return

    logger.info(f"🚀 STARTING BULK INGESTION")
    logger.info(f"📂 Target Directory: {raw_dir}")
    logger.info(f"📄 File Count: {len(files)}")
    logger.info("="*50)

    # 3. INITIALIZE PIPELINES
    # This sets up the Embedding Models and DB Connections once.
    try:
        ingest_pipe = IngestionPipeline()
        index_pipe = IndexingPipeline()
    except Exception as e:
        logger.critical(f"Failed to initialize pipelines: {e}")
        return

    success_count = 0
    failed_files = []

    # 4. PROCESS LOOP
    for i, file_path in enumerate(files, 1):
        try:
            logger.info(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
            
            # --- PHASE 1: INGESTION (Load -> Clean -> Chunk) ---
            nodes = ingest_pipe.run(str(file_path))
            
            if not nodes:
                logger.warning(f"⏭️ Skipping {file_path.name}: No usable content extracted.")
                failed_files.append(f"{file_path.name} (Empty)")
                continue

            # --- PHASE 2: INDEXING (Vector DB) ---
            # index_pipe.run handles the "Delete Old Version" logic internally
            result_index = index_pipe.run(nodes)
            
            if result_index:
                success_count += 1
                logger.info(f"✅ COMPLETED: {file_path.name}")
            else:
                logger.error(f"DB ERROR: {file_path.name}")
                failed_files.append(f"{file_path.name} (DB Fail)")

        except Exception as e:
            logger.error(f"CRASHED: {file_path.name} -> {e}")
            failed_files.append(f"{file_path.name} (Exception: {str(e)})")
        print("="*100)

    # 5. SUMMARY REPORT
    duration = time.time() - start_time
    logger.info("\n" + "="*50)
    logger.info(f"🏁 BULK INGESTION COMPLETE")
    logger.info(f"⏱️ Time Taken: {duration:.2f} seconds")
    logger.info(f"✅ Success: {success_count}")
    logger.info(f"❌ Failed:  {len(failed_files)}")
    
    if failed_files:
        logger.info("\n⚠️ Failed Files List:")
        for f in failed_files:
            logger.info(f" - {f}")
            
    logger.info("="*50)

if __name__ == "__main__":
    main()











# # 7k
# import os
# import sys
# import logging
# import time
# from pathlib import Path
# from dotenv import load_dotenv

# # Path Setup
# project_root = Path(__file__).resolve().parent.parent
# sys.path.append(str(project_root))

# load_dotenv()

# from src.core.logger import setup_logger
# from src.ingestion import IngestionPipeline
# from src.indexing import IndexingPipeline
# from src.config import settings

# # Qdrant Filters for checking existence
# from qdrant_client.http import models

# logger = setup_logger("BATCH_PROCESSOR")

# def file_already_indexed(qdrant_manager, filename: str) -> bool:
#     """
#     Checks Qdrant to see if this filename already exists.
#     This allows us to STOP and RESUME the script without re-doing 7000 files.
#     """
#     try:
#         # Create a filter for the specific filename
#         filter_condition = models.Filter(
#             must=[
#                 models.FieldCondition(
#                     key="file_name", 
#                     match=models.MatchValue(value=filename)
#                 )
#             ]
#         )
        
#         # We only need 1 result to know it exists
#         res = qdrant_manager.client.scroll(
#             collection_name=settings.COLLECTION_NAME,
#             scroll_filter=filter_condition,
#             limit=1
#         )
        
#         # scroll returns (points, next_page_offset)
#         # If points list is not empty, the file exists.
#         return len(res[0]) > 0

#     except Exception:
#         # If DB is down or collection doesn't exist yet, assume false
#         return False

# def main():
#     start_time = time.time()
    
#     # 1. SETUP
#     raw_dir = settings.RAW_SOPS_DIR
#     if not raw_dir.exists():
#         logger.error(f"❌ Missing Directory: {raw_dir}")
#         return

#     # Scan for files
#     valid_exts = ['.pdf', '.docx', '.doc']
#     all_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in valid_exts]
    
#     if not all_files:
#         logger.warning("No files found.")
#         return

#     logger.info(f"🚀 DETECTED {len(all_files)} FILES. Starting Smart Ingestion...")

#     # 2. INIT PIPELINES
#     try:
#         ingest_pipe = IngestionPipeline()
#         index_pipe = IndexingPipeline()
#         # Access the raw DB manager to check for existing files
#         db_manager = index_pipe.db_manager 
#     except Exception as e:
#         logger.critical(f"Pipeline Init Failed: {e}")
#         return

#     # 3. PROCESSING LOOP
#     processed = 0
#     skipped = 0
#     failed = []

#     for i, file_path in enumerate(all_files, 1):
#         filename = file_path.name
        
#         print(f"\n[{i}/{len(all_files)}] Checking: {filename} ...", end=" ", flush=True)

#         # --- CHECK: ALREADY EXISTS? ---
#         if file_already_indexed(db_manager, filename):
#             print("✅ ALREADY INDEXED. SKIPPING.")
#             skipped += 1
#             continue

#         # --- PROCESS ---
#         try:
#             print("⏳ PROCESSING...")
            
#             # A. Ingest
#             nodes = ingest_pipe.run(str(file_path))
            
#             if not nodes:
#                 print("⚠️ EMPTY / FAILED PARSE.")
#                 failed.append(filename)
#                 continue
            
#             # B. Index
#             index_pipe.run(nodes)
            
#             print(f"🎉 DONE. Added {len(nodes)} chunks.")
#             processed += 1

#         except Exception as e:
#             print(f"❌ ERROR: {e}")
#             logger.error(f"Failed {filename}: {e}")
#             failed.append(filename)

#     # 4. REPORT
#     total_time = time.time() - start_time
#     logger.info("="*50)
#     logger.info(f"BATCH COMPLETE in {total_time/60:.2f} minutes")
#     logger.info(f"🆕 Processed: {processed}")
#     logger.info(f"⏭️ Skipped (Exists): {skipped}")
#     logger.info(f"❌ Failed: {len(failed)}")
#     logger.info("="*50)

# if __name__ == "__main__":
#     main()