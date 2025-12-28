from typing import List
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SentenceSplitter

class PDFChunker:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_nodes(self, nodes: List[TextNode]) -> List[TextNode]:
        """
        Splits a list of page-level TextNodes into smaller chunks.
        """
        if not nodes:
            return []

        # get_nodes_from_documents handles the splitting while preserving metadata
        final_nodes = self.splitter.get_nodes_from_documents(nodes)
        
        print(f"Generated {len(final_nodes)} chunks from {len(nodes)} pages.")
        return final_nodes