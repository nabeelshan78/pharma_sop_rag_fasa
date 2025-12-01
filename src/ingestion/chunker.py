import logging
import re
from typing import List, Optional
from llama_index.core import Document
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

# Robust logger import
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class SOPChunker:
    """
    Hybrid Chunker: Markdown Aware + Token Safe + Context Injecting.
    
    Responsibilities:
    1. Splits strictly by Markdown Headers (#, ##).
    2. 'Rebalances' orphan headers (headers stranded at the bottom of a chunk).
    3. Injects SOP Metadata (Title, Version) directly into the text for better vector retrieval.
    """
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        # Parses structure (# H1, ## H2)
        self.markdown_parser = MarkdownNodeParser(include_metadata=True)
        # Safety net for massive sections that exceed token limits
        self.text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _get_header_path(self, node: TextNode) -> str:
        """Extracts the breadcrumb path (e.g., '5.0 Responsibilities > 5.1 Manager')."""
        header_path = node.metadata.get("header_path", "")
        return header_path.replace("/", " > ") if header_path else "General Section"

    def _rebalance_headers(self, nodes: List[TextNode]) -> List[TextNode]:
        """
        Step 1.5 Logic:
        Scans raw Markdown nodes. If a node ends in a header (orphan),
        it pushes that header to the start of the NEXT node.
        """
        if not nodes:
            return []
            
        cleaned_nodes = []
        # Regex: Matches a Header line at the very end of the text
        # (?:^|\n)      -> Start of line
        # (#{1,6}\s+.*) -> The Header (Group 1)
        # \s*$          -> End of string
        orphan_pattern = re.compile(r'(?:^|\n)(#{1,6}\s+[^\n]+)\s*$', re.DOTALL)

        i = 0
        while i < len(nodes):
            current_node = nodes[i]
            
            # If we are at the very last node, we can't push anything forward.
            if i == len(nodes) - 1:
                if current_node.text.strip():
                    cleaned_nodes.append(current_node)
                break
            
            next_node = nodes[i+1]
            
            # Check current node for orphan header
            match = orphan_pattern.search(current_node.text)
            
            if match:
                header_text = match.group(1)
                
                # LOGIC CHECK: Only merge if they belong to the same file
                curr_src = current_node.metadata.get("file_name", "A")
                next_src = next_node.metadata.get("file_name", "B")
                
                if curr_src == next_src:
                    logger.debug(f"🩹 Moving orphan header '{header_text.strip()}' from Node {i} to Node {i+1}")
                    
                    # 1. Remove header from current node
                    cut_index = match.start()
                    current_node.text = current_node.text[:cut_index].strip()
                    
                    # 2. Prepend header to next node
                    next_node.text = f"{header_text}\n\n{next_node.text}"
                    
                    # 3. If current node is now empty (it was ONLY a header), drop it.
                    if current_node.text:
                        cleaned_nodes.append(current_node)
                    
                    # Move to next
                    i += 1
                    continue

            # Default: Add node and move on
            cleaned_nodes.append(current_node)
            i += 1
            
        return cleaned_nodes

    def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
        """
        Main pipeline: Markdown Split -> Rebalance -> Token Limit -> Context Injection.
        """
        if not documents:
            logger.warning("No documents provided to chunker.")
            return []

        logger.info(f"✂️ Chunking {len(documents)} document(s)...")
        
        try:
            # 1. Structural Split (Markdown)
            # This creates nodes based on headers.
            base_nodes = self.markdown_parser.get_nodes_from_documents(documents)
            
            # 2. Rebalance Orphans
            # Fixes cases where a header was left behind at the end of a page/node.
            base_nodes = self._rebalance_headers(base_nodes)
            
            final_nodes = []
            
            for node in base_nodes:
                # 3. Safety Split (Token Limit)
                # If a section is 5000 chars, it's too big for embedding. Split it further.
                sub_nodes = [node]
                if len(node.text) > 2000: # Conservative limit
                    # Wrap in Document to use splitter
                    temp_doc = Document(text=node.text, metadata=node.metadata)
                    sub_nodes = self.text_splitter.get_nodes_from_documents([temp_doc])
                
                # 4. Context Injection
                for sub_node in sub_nodes:
                    # Extract Metadata (Fail gracefully if missing)
                    sop_title = sub_node.metadata.get("sop_title", sub_node.metadata.get("file_name", "Unknown SOP"))
                    version = sub_node.metadata.get("version_original", "N/A") # Matches versioning.py
                    page_label = sub_node.metadata.get("page_label", "N/A")
                    header_context = self._get_header_path(sub_node)

                    # Construct the "Zero Hallucination" Header
                    # This text is baked into the vector, so the AI knows EXACTLY where this came from.
                    context_str = (
                        f"CONTEXT: Doc: {sop_title} | Ver: {version} | Page: {page_label}\n"
                        f"SECTION: {header_context}\n"
                        f"{'-'*30}\n"
                    )
                    
                    # Create NEW TextNode to ensure we don't mutate references oddly
                    new_node = TextNode(
                        text=context_str + sub_node.text,
                        id_=sub_node.node_id, # Keep ID for traceability
                        metadata=sub_node.metadata.copy(),
                        relationships=sub_node.relationships
                    )
                    
                    # Add specific metadata for the Retriever to use later
                    new_node.metadata["context_header"] = header_context
                    
                    final_nodes.append(new_node)

            # 5. Re-link Relationships (Prev/Next)
            # Critical for "Window Retrieval" (getting the chunk before/after)
            for i in range(len(final_nodes)):
                if i > 0:
                    final_nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=final_nodes[i-1].node_id)
                if i < len(final_nodes) - 1:
                    final_nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=final_nodes[i+1].node_id)

            logger.info(f"✅ Chunking Complete. Generated {len(final_nodes)} structured chunks.")
            return final_nodes

        except Exception as e:
            logger.error(f"Chunking failed: {e}", exc_info=True)
            raise e



# --- SELF TEST ---
if __name__ == "__main__":
    print("--- Running Chunker Logic Test ---")
    
    # 1. Simulate a Doc that has an "Orphan Header" at the end
    text_part_1 = """
    # 1.0 Introduction
    This is the intro text.
    
    ## 2.0 Scope
    """ # <--- Orphan Header!
    
    text_part_2 = """
    This scope applies to all departments.
    End of scope.
    """
    
    doc1 = Document(text=text_part_1, metadata={"file_name": "SOP_A.pdf", "sop_title": "SOP A", "version_original": "1.0", "page_label": "1"})
    doc2 = Document(text=text_part_2, metadata={"file_name": "SOP_A.pdf", "sop_title": "SOP A", "version_original": "1.0", "page_label": "1"})
    
    # 2. Run Chunker
    chunker = SOPChunker()
    # We simulate them coming from the parser as nodes first for the unit test
    node1 = TextNode(text=text_part_1, metadata=doc1.metadata)
    node2 = TextNode(text=text_part_2, metadata=doc2.metadata)
    
    print("Rebalancing Headers...")
    cleaned = chunker._rebalance_headers([node1, node2])
    
    print(f"\nNode 1 Text (Should NOT have header):\n---\n{cleaned[0].text}\n---")
    print(f"\nNode 2 Text (SHOULD have header):\n---\n{cleaned[1].text}\n---")
    
    if "## 2.0 Scope" in cleaned[1].text and "## 2.0 Scope" not in cleaned[0].text:
        print("\n✅ SUCCESS: Orphan header moved correctly.")
    else:
        print("\n❌ FAIL: Header rebalancing failed.")