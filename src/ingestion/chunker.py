import logging
import re
from typing import List
from llama_index.core import Document
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPChunker:
    """
    Hybrid Chunker: Markdown Aware + Token Safe + Context Injecting.
    FIX: Rebalances orphan headers BEFORE context injection.
    """
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        self.markdown_parser = MarkdownNodeParser()
        self.text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _get_header_path(self, node: TextNode) -> str:
        header_path = node.metadata.get("header_path", "")
        return header_path.replace("/", " > ") if header_path else "General Section"

    def _rebalance_headers(self, nodes: List[TextNode]) -> List[TextNode]:
        """
        Step 1.5 Logic:
        Scans raw Markdown nodes. If a node is JUST a header, or ENDS in a header,
        it pushes that header to the start of the NEXT node.
        """
        if not nodes:
            return []
            
        cleaned_nodes = []
        # Regex explanation:
        # (?:^|\n)      -> Match start of string OR a newline
        # (#{1,6}\s+.*) -> Match # Header Text (Group 1)
        # \s*$          -> Match end of string (ignoring trailing spaces)
        orphan_pattern = re.compile(r'(?:^|\n)(#{1,6}\s+[^\n]+)\s*$', re.DOTALL)

        i = 0
        while i < len(nodes):
            current_node = nodes[i]
            
            # If we are at the very last node, we can't push anything forward.
            if i == len(nodes) - 1:
                if current_node.text.strip(): # Only add if not empty
                    cleaned_nodes.append(current_node)
                break
            
            next_node = nodes[i+1]
            
            # Check current node for orphan header
            match = orphan_pattern.search(current_node.text)
            
            if match:
                header_text = match.group(1)
                
                # LOGIC CHECK: Only merge if they belong to the same file
                # (Prevents merging the last header of File A into File B)
                curr_src = current_node.metadata.get("filename", "A")
                next_src = next_node.metadata.get("filename", "B")
                
                if curr_src == next_src:
                    logger.debug(f"🩹 Moving orphan header '{header_text.strip()}' to next chunk.")
                    
                    # 1. Remove header from current node
                    # We cut the text before the match starts
                    cut_index = match.start()
                    current_node.text = current_node.text[:cut_index].strip()
                    
                    # 2. Prepend header to next node
                    next_node.text = f"{header_text}\n\n{next_node.text}"
                    
                    # 3. If current node is now empty (it was ONLY a header), don't append it
                    if current_node.text:
                        cleaned_nodes.append(current_node)
                    
                    # Note: We do NOT increment i here for next_node, 
                    # because we modified next_node in place and it might need checking too!
                    i += 1
                    continue

            # Default: Add node and move on
            cleaned_nodes.append(current_node)
            i += 1
            
        return cleaned_nodes

    def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
        if not documents:
            return []

        logger.info(f"✂️ Chunking {len(documents)} document(s)...")
        
        # 1. Structural Split (Markdown)
        base_nodes = self.markdown_parser.get_nodes_from_documents(documents)
        
        # --- FIX: REBALANCE HEADERS HERE ---
        # We fix the orphans BEFORE we mess with context strings or token splitting
        base_nodes = self._rebalance_headers(base_nodes)
        
        final_nodes = []
        
        for node in base_nodes:
            # 2. Safety Split (Token Limit)
            sub_nodes = [node]
            if len(node.text) > 3000:
                # Wrap in Document to use splitter
                temp_doc = Document(text=node.text, metadata=node.metadata)
                sub_nodes = self.text_splitter.get_nodes_from_documents([temp_doc])
            
            # 3. Context Injection
            for sub_node in sub_nodes:
                sop_name = sub_node.metadata.get("sop_title", sub_node.metadata.get("filename", "Unknown"))
                version = sub_node.metadata.get("version", "N/A")
                page_label = sub_node.metadata.get("page_label", "N/A")
                header_context = self._get_header_path(sub_node)

                context_str = (
                    f"CONTEXT: Doc: {sop_name} | Ver: {version} | Page: {page_label}\n"
                    f"SECTION: {header_context}\n"
                    f"{'-'*30}\n"
                )
                
                # Create NEW TextNode (Pydantic fix)
                new_node = TextNode(
                    text=context_str + sub_node.text,
                    metadata=sub_node.metadata.copy(),
                    relationships=sub_node.relationships
                )
                
                new_node.metadata["context_header"] = header_context
                final_nodes.append(new_node)

        # 4. Re-link Relationships
        for i in range(len(final_nodes)):
            if i > 0:
                final_nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=final_nodes[i-1].node_id)
            if i < len(final_nodes) - 1:
                final_nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=final_nodes[i+1].node_id)

        logger.info(f"✅ Chunking Complete. Generated {len(final_nodes)} chunks.")
        return final_nodes





# import logging
# from typing import List, Optional
# from llama_index.core import Document
# from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
# from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# from src.core.logger import setup_logger

# logger = setup_logger(__name__)

# class SOPChunker:
#     """
#     Hybrid Chunker designed for Pharmaceutical SOPs.
    
#     Strategy:
#     1. Structure-Aware: Splits first by Markdown Headers (#, ##, ###).
#     2. Token-Safe: If a section is too large, sub-splits using sentence boundaries.
#     3. Context-Rich: Injects SOP Metadata + Breadcrumbs into EVERY chunk's text.
#     """
    
#     def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
#         # 1. The Architect: Understands formatting, tables, and headers
#         self.markdown_parser = MarkdownNodeParser()
        
#         # 2. The Butcher: Ensures no chunk exceeds token limits (Safety Net)
#         self.text_splitter = SentenceSplitter(
#             chunk_size=chunk_size, 
#             chunk_overlap=chunk_overlap
#         )

#     def _get_header_path(self, node: TextNode) -> str:
#         """Extracts and formats the header path (e.g., '5. Process > 5.1 Mixing')."""
#         # LlamaIndex stores header paths in metadata usually as 'header_1/header_2'
#         # We try to fetch it, otherwise return "General"
#         header_path = node.metadata.get("header_path", "")
#         if not header_path:
#             return "General Section"
        
#         # Convert "Header 1/Header 2" -> "Header 1 > Header 2" for readability
#         return header_path.replace("/", " > ")

#     def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
#         """
#         Main pipeline: Markdown Parse -> Limit Check -> Context Injection.
#         """
#         if not documents:
#             logger.warning("No documents provided to chunker.")
#             return []

#         logger.info(f"Chunking {len(documents)} document(s)...")
        
#         # Step 1: Structural Split (Markdown)
#         # This keeps tables intact and groups text by logical sections.
#         base_nodes = self.markdown_parser.get_nodes_from_documents(documents)
        
#         final_nodes = []
        
#         for node in base_nodes:
#             # Copy essential metadata from the parent document if not present
#             # (MarkdownNodeParser sometimes drops custom metadata depending on version)
#             source_doc = documents[0] # Simplification: Assuming batch belongs to same file context
#             # In a mixed batch, you'd match node.ref_doc_id to document.doc_id, 
#             # but LlamaIndex usually handles inheritance. We ensure specific keys exist:
            
#             # Step 2: Safety Check (Size Limit)
#             # If the Markdown section is massive (e.g., 2000 tokens), split it further.
#             sub_nodes = [node]
#             if len(node.text) > 3000: # Rough char count (~750 tokens) check before expensive token split
#                 sub_nodes = self.text_splitter.get_nodes_from_documents([node.to_document()])
            
#             # Step 3: Context Injection Loop
#             for sub_node in sub_nodes:
#                 # Extract Metadata
#                 sop_name = sub_node.metadata.get("sop_title", sub_node.metadata.get("filename", "Unknown SOP"))
#                 version = sub_node.metadata.get("version", "N/A")
#                 page_label = sub_node.metadata.get("page_label", "N/A")
#                 header_context = self._get_header_path(sub_node)

#                 # Create the Context Header
#                 # This string is what the Embedding Model reads first!
#                 context_str = (
#                     f"CONTEXT: Doc: {sop_name} | Ver: {version} | Page: {page_label}\n"
#                     f"SECTION: {header_context}\n"
#                     f"{'-'*30}\n"
#                 )
                
#                 # Prepend to text (Permanent binding of context to content)
#                 sub_node.text = context_str + sub_node.text
                
#                 # Ensure metadata is clean for the vector store
#                 sub_node.metadata["context_header"] = header_context
                
#                 final_nodes.append(sub_node)

#         # Step 4: Re-establish Relationships
#         # Because we might have sub-split nodes, we need to link them linearly (Prev/Next)
#         for i in range(len(final_nodes)):
#             if i > 0:
#                 final_nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=final_nodes[i-1].node_id)
#             if i < len(final_nodes) - 1:
#                 final_nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=final_nodes[i+1].node_id)

#         logger.info(f"Chunking Complete. Generated {len(final_nodes)} chunks from {len(documents)} docs.")
#         return final_nodes





# # --- TEST BLOCK ---
# if __name__ == "__main__":
#     # Create a dummy document to test
#     dummy_text = """
#     # 5. Production Process
    
#     ## 5.1 Mixing
#     The mixing process must be done at 25C.
    
#     | Ingredient | Amount |
#     |---|---|
#     | Water | 100L |
#     | Salt | 5kg |
    
#     ## 5.2 Storage
#     Store in a cool dry place.
#     """
    
#     doc = Document(
#         text=dummy_text, 
#         metadata={"sop_title": "SOP-005 Production", "version": "2.0", "page_label": "5"}
#     )
    
#     chunker = SOPChunker()
#     nodes = chunker.chunk_documents([doc])
    
#     print(f"Generated {len(nodes)} chunks.\n")
#     for i, n in enumerate(nodes):
#         print(f"--- CHUNK {i+1} ---")
#         print(n.text[:200]) # Print first 200 chars to see context
#         print("...\n")











# # ingestion/chunker.py
# # Role: Logic-aware splitting. It groups text by headers first, then splits by size.

# import re
# from typing import List, Dict, Set, Any
# from unstructured.documents.elements import Title, Header

# from llama_index.core import Document
# from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
# from llama_index.core.node_parser import SentenceSplitter

# from src.core.logger import setup_logger
# # This ensures consistent formatting across the whole app
# logger = setup_logger(__name__)

# class SemanticChunker:
#     """
#     Groups elements by Logical Sections (Headers) first, 
#     then applies a safety SentenceSplitter for context window limits.
#     """
    
#     def __init__(self, chunk_size=1024, chunk_overlap=200):
#         self.safety_splitter = SentenceSplitter(
#             chunk_size=chunk_size, 
#             chunk_overlap=chunk_overlap
#         )

#     def _is_header(self, element, text) -> bool:
#         """Detects if an element is a section header."""
#         # 1. Trust Unstructured metadata
#         if isinstance(element, (Title, Header)):
#             return True
#         # 2. Fallback Regex (e.g., "1.0 Introduction" or "SECTION A")
#         if re.match(r"^(\d+(\.\d+)*)\.?\s+[A-Z][A-Z\s]{2,}$", text.strip()):
#             return True
#         return False

#     def group_and_split(self, elements: List[Any], base_metadata: Dict) -> List[TextNode]:
#         """
#         1. Aggregates text into sections based on headers.
#         2. Creates LlamaIndex Documents.
#         3. Splits large sections using Safety Splitter.
#         """
#         section_docs = []
        
#         current_section = "General / Prologue"
#         current_buffer = []
#         current_pages: Set[int] = set()

#         for el in elements:
#             text = el.text # Assuming text is already cleaned by Cleaner
            
#             if self._is_header(el, text):
#                 # Flush previous section
#                 self._flush_buffer(section_docs, current_buffer, current_section, current_pages, base_metadata)
                
#                 # Start new section
#                 current_section = text
#                 current_buffer = [text] # Include header in the new chunk context
#                 current_pages = {el.metadata.page_number} if hasattr(el.metadata, 'page_number') else set()
#             else:
#                 current_buffer.append(text)
#                 if hasattr(el.metadata, 'page_number') and el.metadata.page_number:
#                     current_pages.add(el.metadata.page_number)

#         # Final Flush
#         self._flush_buffer(section_docs, current_buffer, current_section, current_pages, base_metadata)

#         # Apply Safety Splitter (transforms Docs -> Nodes)
#         return self._create_linked_nodes(section_docs)

#     def _flush_buffer(self, docs_list, buffer, section_title, pages, base_meta):
#         if not buffer:
#             return
        
#         full_text = "\n\n".join(buffer)
#         if len(full_text) < 50: # Skip noise sections
#             return

#         meta = base_meta.copy()
#         meta["section"] = section_title
#         meta["page_numbers"] = ",".join(map(str, sorted(list(pages))))
        
#         docs_list.append(Document(text=full_text, metadata=meta))

#     def _create_linked_nodes(self, documents: List[Document]) -> List[TextNode]:
#         """Runs the splitter and links nodes for context."""
#         nodes = self.safety_splitter.get_nodes_from_documents(documents)
        
#         for i in range(len(nodes)):
#             if i > 0:
#                 nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=nodes[i-1].node_id)
#             if i < len(nodes) - 1:
#                 nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=nodes[i+1].node_id)
                
#         return nodes