import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Import our new Master Pipeline
from src.ingestion import IngestionPipeline
from src.core.logger import setup_logger

# Setup Logger
logger = setup_logger(__name__)

# Load Env (for API Keys)
load_dotenv()

async def main():
    # ---------------------------------------------------------
    # 1. CONFIGURATION
    # ---------------------------------------------------------
    # Update this path to one of your real PDF files
    # Using raw string r"..." handles Windows backslashes automatically
    target_file = r"data\raw_sops\GRT_PROC_English_stamped_V7.docmNov302025052354.pdf"
    
    # Check if file exists before running
    if not os.path.exists(target_file):
        logger.error(f"❌ File not found: {target_file}")
        logger.info("Please update the 'target_file' variable in test_ingestion.py")
        return

    # ---------------------------------------------------------
    # 2. RUN THE PIPELINE
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"🧪 TESTING INGESTION PIPELINE")
    print(f"{'='*60}\n")
    
    # Initialize the pipeline (Loader -> Cleaner -> Chunker -> Versioning)
    pipeline = IngestionPipeline()
    
    # Run process (Async)
    nodes = await pipeline.process_file(target_file)

    # ---------------------------------------------------------
    # 3. INSPECT RESULTS
    # ---------------------------------------------------------
    if not nodes:
        print("\n❌ No nodes generated. Something went wrong.")
        return

    print(f"\n✅ SUCCESS! Generated {len(nodes)} chunks.")
    # inspect all nodes
    for i, node in enumerate(nodes):
        print(f"\n{'='*10} Chunk {i+1} {'='*10}")
        print(f"Metadata: {node.metadata}")
        print(f"Text Snippet: {node.text}")
        print(f"{'='*100}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())