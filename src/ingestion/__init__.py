import os
from typing import List

from llama_index.core.schema import TextNode

# Import the modular components
from .loader import PDFLoader
from .chunker import PDFChunker

class IngestionPipeline:
    """
    FASA Ingestion Pipeline.
    """
    
    def __init__(self):
        print(">>>>>>>>>>>>>>>>>      Initializing FASA Ingestion Pipeline components...")
        
        # Initialize the modular components
        self.loader = PDFLoader()
        self.chunker = PDFChunker()
        
        print(">>>>>>>>>>>>>>>>>      Pipeline components initialized successfully.")

    def run(self, file_path: str) -> List[TextNode]:
        """
        Executes the full end-to-end pipeline for a single file.
        """
        try:
            file_name = os.path.basename(file_path)
            print(f">>>>>>>>>>>>>>>>>>> STARTING PIPELINE for: {file_name}")
            page_nodes = self.loader.load_pdf(file_path)
            if not page_nodes:
                print(f"Step [Loader]: No valid pages extracted for {file_name}.")
                return []

            nodes = self.chunker.chunk_nodes(page_nodes)            
            if not nodes:
                print(f"Step [Chunker]: No valid chunks generated (all filtered out) for {file_name}.")
                return []
            print(f">>>>>>>>>>>>>>>>>>> FINISHED PIPELINE: Generated {len(nodes)} high-quality vector nodes.")
            return nodes

        except Exception as e:
            print(f">>>>>>>>>>>>>>>>>>> PIPELINE CRASHED for {file_path}: {str(e)}")
            return []

# Expose the class and modules for external use
__all__ = ["IngestionPipeline", "PDFLoader", "PDFChunker"]