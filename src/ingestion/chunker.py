# ingestion/chunker.py
# Role: Logic-aware splitting. It groups text by headers first, then splits by size.

import re
from typing import List, Dict, Set, Any
from unstructured.documents.elements import Title, Header

from llama_index.core import Document
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import SentenceSplitter

from src.core.logger import setup_logger
# This ensures consistent formatting across the whole app
logger = setup_logger(__name__)

class SemanticChunker:
    """
    Groups elements by Logical Sections (Headers) first, 
    then applies a safety SentenceSplitter for context window limits.
    """
    
    def __init__(self, chunk_size=1024, chunk_overlap=200):
        self.safety_splitter = SentenceSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )

    def _is_header(self, element, text) -> bool:
        """Detects if an element is a section header."""
        # 1. Trust Unstructured metadata
        if isinstance(element, (Title, Header)):
            return True
        # 2. Fallback Regex (e.g., "1.0 Introduction" or "SECTION A")
        if re.match(r"^(\d+(\.\d+)*)\.?\s+[A-Z]", text):
            return True
        return False

    def group_and_split(self, elements: List[Any], base_metadata: Dict) -> List[TextNode]:
        """
        1. Aggregates text into sections based on headers.
        2. Creates LlamaIndex Documents.
        3. Splits large sections using Safety Splitter.
        """
        section_docs = []
        
        current_section = "General / Prologue"
        current_buffer = []
        current_pages: Set[int] = set()

        for el in elements:
            text = el.text # Assuming text is already cleaned by Cleaner
            
            if self._is_header(el, text):
                # Flush previous section
                self._flush_buffer(section_docs, current_buffer, current_section, current_pages, base_metadata)
                
                # Start new section
                current_section = text
                current_buffer = [text] # Include header in the new chunk context
                current_pages = {el.metadata.page_number} if hasattr(el.metadata, 'page_number') else set()
            else:
                current_buffer.append(text)
                if hasattr(el.metadata, 'page_number') and el.metadata.page_number:
                    current_pages.add(el.metadata.page_number)

        # Final Flush
        self._flush_buffer(section_docs, current_buffer, current_section, current_pages, base_metadata)

        # Apply Safety Splitter (transforms Docs -> Nodes)
        return self._create_linked_nodes(section_docs)

    def _flush_buffer(self, docs_list, buffer, section_title, pages, base_meta):
        if not buffer:
            return
        
        full_text = "\n\n".join(buffer)
        if len(full_text) < 50: # Skip noise sections
            return

        meta = base_meta.copy()
        meta["section"] = section_title
        meta["page_numbers"] = ",".join(map(str, sorted(list(pages))))
        
        docs_list.append(Document(text=full_text, metadata=meta))

    def _create_linked_nodes(self, documents: List[Document]) -> List[TextNode]:
        """Runs the splitter and links nodes for context."""
        nodes = self.safety_splitter.get_nodes_from_documents(documents)
        
        for i in range(len(nodes)):
            if i > 0:
                nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=nodes[i-1].node_id)
            if i < len(nodes) - 1:
                nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=nodes[i+1].node_id)
                
        return nodes