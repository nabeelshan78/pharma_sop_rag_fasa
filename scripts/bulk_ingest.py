import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load Env Vars
load_dotenv()

# Add project root to path so we can import 'src'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.core.logger import setup_logger
from src.ingestion import IngestionPipeline
from src.indexing import IndexingPipeline

# Setup Logger
logger = setup_logger("BULK_INGEST")

def main():
    """
    Scans data/raw_sops/, processes all files, and indexes them into Qdrant.
    """
    # 1. Check Directory
    raw_dir = settings.DATA_DIR / "raw_sops"
    if not raw_dir.exists():
        logger.error(f"Directory not found: {raw_dir}")
        logger.info("Please create 'data/raw_sops' and put your PDFs there.")
        return

    files = [f for f in raw_dir.iterdir() if f.suffix.lower() in ['.pdf', '.docx', '.txt']]
    
    if not files:
        logger.warning("No files found in data/raw_sops/")
        return

    logger.info(f">>>>>Starting Bulk Ingestion for {len(files)} files...")

    # 2. Initialize Pipelines
    ingest_pipe = IngestionPipeline()
    index_pipe = IndexingPipeline()

    success_count = 0

    # 3. Process Loop
    for file_path in files:
        try:
            logger.info(f">>>>>Processing: {file_path.name}")
            
            # Step A: Ingest (Load -> Clean -> Chunk)
            nodes = ingest_pipe.process_file(str(file_path))
            
            if not nodes:
                logger.warning(f">>>>> No text extracted from {file_path.name}")
                continue

            # Step B: Index (Embed -> Vector DB)
            index_pipe.run(nodes)
            
            success_count += 1
            logger.info(f">>>>> Finished: {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to ingest {file_path.name}: {e}")

    # 4. Summary
    logger.info("="*40)
    logger.info(f">>>>> Bulk Ingestion Complete!")
    logger.info(f"Files Processed: {success_count}/{len(files)}")
    logger.info(f"Vector Database: {settings.COLLECTION_NAME}")
    logger.info("="*100)

if __name__ == "__main__":
    main()