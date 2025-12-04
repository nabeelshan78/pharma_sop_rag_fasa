import re
import logging
from typing import List, Dict, Any

from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import Document, BaseNode

# Internal Logger
from src.core.logger import setup_logger
logger = setup_logger(__name__)

# ========================================================================


class SOPChunker:
    """
    Chunker for Pharmaceutical SOPs.    
    """

    def __init__(self):
        self.parser = MarkdownNodeParser(
            include_metadata=True,
            include_prev_next_rel=True
        )
        self.header_content_pattern = re.compile(r'^#+\s*(\d+(?:\.\d+)*)\.?\s+(.*)', re.MULTILINE)

    def chunk_documents(self, documents: List[Document]) -> List[BaseNode]:
        all_nodes = []
        for doc in documents:
            try:
                if not doc.text: continue
                # Split text into nodes
                raw_nodes = self.parser.get_nodes_from_documents([doc])
                # Enrich nodes
                enriched_nodes = self._enrich_nodes(raw_nodes, doc.metadata)
                all_nodes.extend(enriched_nodes)
            except Exception as e:
                logger.error(f"Failed to chunk document: {e}", exc_info=True)
                continue
        logger.info(f"Chunking complete. Generated {len(all_nodes)} semantic vectors.")
        return all_nodes

    def _enrich_nodes(self, nodes: List[BaseNode], file_metadata: Dict[str, Any]) -> List[BaseNode]:
        enriched = []
        # Track the last valid Section ID to handle "sub-chunks"
        current_section_id = "General"
        current_section_title = "General Context"
        
        for node in nodes:
            # Inherit File Metadata
            for key, value in file_metadata.items():
                if key not in node.metadata:
                    node.metadata[key] = value
            # Force-Extract Metadata from Text Content
            match = self.header_content_pattern.match(node.text)
            
            if match:
                # HIT: This node starts with a Header
                current_section_id = match.group(1).strip()
                current_section_title = match.group(2).strip()
                node.metadata['section_id'] = current_section_id
                node.metadata['section_title'] = current_section_title
                node.metadata['header_path'] = f"{current_section_id} {current_section_title}"
            
            else:
                # MISS: This is a continuation chunk or a pseudo-header chunk
                if node.text.startswith("#"):
                    # It's a header, but no number.
                    clean_title = node.text.split("\n")[0].replace("#", "").strip()
                    node.metadata['section_id'] = current_section_id # Inherit Parent ID
                    node.metadata['section_title'] = clean_title
                    node.metadata['header_path'] = f"{current_section_id} > {clean_title}"
                else:
                    # Pure text continuation
                    node.metadata['section_id'] = current_section_id
                    node.metadata['section_title'] = current_section_title
                    node.metadata['header_path'] = f"{current_section_id} {current_section_title} (Cont.)"
            cleaned_text = node.text.strip()
            
            # Filter
            is_noise_phrase = cleaned_text.lower().replace(".", "") in [
                "not applicable", 
                "none", 
                "n/a", 
                "no cross references"
            ]
            # Drop extremely short chunks
            is_too_short = len(cleaned_text) < 70
            # Apply Filter
            if not is_noise_phrase and not is_too_short:
                node.text = cleaned_text
                enriched.append(node)
            else:
                pass
        return enriched





















# # ==========================================
# #  Testing Block (Runnable)
# # ==========================================
# if __name__ == "__main__":
#     # Simulating the pipeline output from Cleaner
#     print("--- STARTING CHUNKER TEST ---")
    
#     clean_text = """
#     """
    
#     # Create dummy document
#     doc = Document(
#         text=clean_text, 
#         metadata={"file_name": "AT-GE-577-Test.pdf", "sop_id": "AT-GE-577"}
#     )
    
#     chunker = SOPChunker()
#     nodes = chunker.chunk_documents([doc])
    
#     import json
    
#     print(f"\nGenerated {len(nodes)} Chunks.\n")
    
#     for i, node in enumerate(nodes):
#         print(f"--- Chunk {i+1} ---")
#         print(f"ID: {node.metadata.get('section_id')}")
#         print(f"Title: {node.metadata.get('section_title')}")
#         print(f"Path: {node.metadata.get('header_path')}")
#         print(f"Content Preview: {node.text}")
#         print("-" * 20)