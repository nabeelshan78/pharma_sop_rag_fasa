import logging
from pathlib import Path
from typing import List

from llama_index.core.schema import TextNode

# Import our modules
from .loader import DocumentLoader
from .cleaner import DocumentCleaner
from .chunker import SemanticChunker
from .versioning import VersionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self):
        self.loader = DocumentLoader()
        self.cleaner = DocumentCleaner()
        self.chunker = SemanticChunker()
        self.version_manager = VersionManager()

    def process_file(self, file_path: str) -> List[TextNode]:
        """
        Full Pipeline: Load -> Extract Meta -> Clean -> Chunk -> Node
        """
        logger.info(f"Starting pipeline for: {file_path}")
        
        # 1. Metadata & Versioning
        metadata = self.version_manager.extract_metadata(file_path)
        logger.info(f"Detected Metadata: {metadata}")

        # 2. Load
        raw_elements = self.loader.load_file(file_path)
        
        # 3. Clean
        clean_elements = self.cleaner.clean_elements(raw_elements)
        
        # 4. Chunk & Split
        nodes = self.chunker.group_and_split(clean_elements, metadata)
        
        logger.info(f"Generated {len(nodes)} nodes for {metadata['sop_name']}")
        return nodes

    def run_directory(self, input_dir: str) -> List[TextNode]:
        path_obj = Path(input_dir)
        all_nodes = []
        
        if not path_obj.exists():
            logger.error("Input directory does not exist.")
            return []

        # Iterate over supported files
        for file_path in path_obj.iterdir():
            if file_path.suffix.lower() in [".pdf", ".docx", ".txt"]:
                try:
                    nodes = self.process_file(str(file_path))
                    all_nodes.extend(nodes)
                except Exception as e:
                    logger.error(f"Pipeline failed for {file_path}: {e}")
        
        return all_nodes


# Allow running this folder as a script for testing
if __name__ == "__main__":
    # Setup simple test
    data_path = Path(__file__).resolve().parents[1] / "data" / "raw_sops"
    
    pipeline = IngestionPipeline()
    nodes = pipeline.run_directory(str(data_path))
    
    if nodes:
        print(f"\nSuccessfully created {len(nodes)} total nodes.")
        print("--- Sample Node ---")
        print(nodes[0].get_content()[:200])
        print(nodes[0].metadata)