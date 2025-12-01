from typing import List
import logging
from llama_index.core.schema import TextNode

# Import the updated "Gold Standard" modules
from .loader import SOPLoader        # Was DocumentLoader
from .cleaner import DocumentCleaner
from .chunker import SOPChunker      # Was SemanticChunker
from .versioning import VersionManager
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class IngestionPipeline:
    """
    Orchestrates the specific Pharma SOP Ingestion Flow:
    1. Version/Metadata Extraction (Regex)
    2. LlamaParse Loading (PDF -> Markdown Tables)
    3. Noise Cleaning (Regex)
    4. Semantic Chunking (Header + Token Limits + Context Injection)
    """
    
    def __init__(self):
        self.version_manager = VersionManager()
        self.loader = SOPLoader()
        self.cleaner = DocumentCleaner()
        self.chunker = SOPChunker()

    async def process_file(self, file_path: str) -> List[TextNode]:
        """
        Runs the full ingestion pipeline for a single file.
        Returns a list of Context-Enriched TextNodes ready for embedding.
        """
        try:
            logger.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Starting ingestion for: {file_path}")
            
            # 1. EXTRACT METADATA
            # We do this first so we can inject it into the Document object immediately
            metadata = self.version_manager.extract_metadata(file_path)
            logger.debug(f"Metadata detected: {metadata}")
            
            # 2. LOAD (PDF -> Markdown)
            # Pass metadata here so it attaches to every page/document created
            documents = self.loader.load_file(file_path, metadata=metadata)
            if not documents:
                logger.warning(f"No content extracted from {file_path}")
                return []
            
            # 3. CLEAN (Regex Noise Removal)
            # Strips headers, footers, and empty table rows
            clean_docs = self.cleaner.clean_documents(documents)
            
            # 4. CHUNK (Markdown Aware + Context Injection)
            # Splits by Header, then by Token Limit. Injects "SOP Title - Section X" into text.
            nodes = self.chunker.chunk_documents(clean_docs)
            
            logger.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Finished {file_path}: Generated {len(nodes)} chunks.")
            return nodes

        except Exception as e:
            logger.error(f"Pipeline failed for {file_path}: {str(e)}", exc_info=True)
            # Return empty list so the batch processor continues to the next file
            return []
    



# import logging
# from pathlib import Path
# from typing import List

# from llama_index.core.schema import TextNode

# # import sys
# # sys.path.append(str(Path(__file__).resolve().parents[2]))

# # Import our modules
# # from src.ingestion.loader import DocumentLoader
# # from src.ingestion.cleaner import DocumentCleaner
# # from src.ingestion.chunker import SemanticChunker
# # from src.ingestion.versioning import VersionManager
# from .loader import DocumentLoader
# from .cleaner import DocumentCleaner
# from .chunker import SemanticChunker
# from .versioning import VersionManager

# from src.core.logger import setup_logger
# # This ensures consistent formatting across the whole app
# logger = setup_logger(__name__)


# class IngestionPipeline:
#     def __init__(self):
#         self.loader = DocumentLoader()
#         self.cleaner = DocumentCleaner()
#         self.chunker = SemanticChunker()
#         self.version_manager = VersionManager()

#     def process_file(self, file_path: str) -> List[TextNode]:
#         """
#         Full Pipeline: Load -> Extract Meta -> Clean -> Chunk -> Node
#         """
#         logger.info(f"Starting pipeline for: {file_path}")
        
#         # 1. Metadata & Versioning
#         metadata = self.version_manager.extract_metadata(file_path)
#         logger.info(f"Detected Metadata: {metadata}")

#         # 2. Load
#         raw_elements = self.loader.load_file(file_path)
        
#         # 3. Clean
#         clean_elements = self.cleaner.clean_elements(raw_elements)
        
#         # 4. Chunk & Split
#         nodes = self.chunker.group_and_split(clean_elements, metadata)
        
#         logger.info(f"Generated {len(nodes)} nodes for {metadata['sop_name']}")
#         return nodes

#     def run_directory(self, input_dir: str) -> List[TextNode]:
#         path_obj = Path(input_dir)
#         all_nodes = []
        
#         if not path_obj.exists():
#             logger.error("Input directory does not exist.")
#             return []

#         # Iterate over supported files
#         for file_path in path_obj.iterdir():
#             if file_path.suffix.lower() in [".pdf", ".docx", ".txt"]:
#                 try:
#                     nodes = self.process_file(str(file_path))
#                     all_nodes.extend(nodes)
#                 except Exception as e:
#                     logger.error(f"Pipeline failed for {file_path}: {e}")
        
#         return all_nodes


# # # Allow running this folder as a script for testing
# # if __name__ == "__main__":
# #     # Setup simple test
# #     data_path = Path(__file__).resolve().parents[2] / "data" / "raw_sops"
    
# #     pipeline = IngestionPipeline()
# #     nodes = pipeline.run_directory(str(data_path))
    
# #     if nodes:
# #         print(f"\nSuccessfully created {len(nodes)} total nodes.")
# #     for node in nodes[:5]:
# #         print(f"\nNode Content:\n{node.get_content()}\nMetadata: {node.metadata}")