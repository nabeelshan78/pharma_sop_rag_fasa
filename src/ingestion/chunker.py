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

        logger.info(f"Chunking {len(documents)} document(s)...")
        
        try:
            # 1. Structural Split (Markdown)
            base_nodes = self.markdown_parser.get_nodes_from_documents(documents)
            # 2. Rebalance Orphans
            base_nodes = self._rebalance_headers(base_nodes)

            final_nodes = []
            for node in base_nodes:
                # 3. Safety Split (Token Limit), If a section is 5000 chars, it's too big for embedding. Split it further.
                sub_nodes = [node]
                if len(node.text) > 2000: 
                    temp_doc = Document(text=node.text, metadata=node.metadata)
                    sub_nodes = self.text_splitter.get_nodes_from_documents([temp_doc])
                
                # 4. Context Injection
                for sub_node in sub_nodes:
                    # Extract Metadata (Fail gracefully if missing)
                    sop_title = sub_node.metadata.get("sop_title", sub_node.metadata.get("file_name", "Unknown SOP"))
                    version = sub_node.metadata.get("version_original", "N/A")
                    page_label = sub_node.metadata.get("page_label", "N/A")
                    header_context = self._get_header_path(sub_node)

                    # Construct the "Zero Hallucination" Header, This text is baked into the vector, so the AI knows EXACTLY where this came from.
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

            logger.info(f"Chunking Complete. Generated {len(final_nodes)} structured chunks.")
            return final_nodes

        except Exception as e:
            logger.error(f"Chunking failed: {e}", exc_info=True)
            raise e





if __name__ == "__main__":
    import json
    import os
    import sys
    # We need Document to load the input
    from llama_index.core import Document

    # 1. Define Paths (Matching your Cleaner output)
    INPUT_FILE = "test_outputs/test_documents_cleaned.jsonl"
    OUTPUT_FILE = "test_outputs/test_documents_chunked.jsonl"

    print("--- FASA Chunker Diagnostic ---")

    # 2. Validate Input
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        print("Tip: Run src/ingestion/cleaner.py first to generate the input.")
        sys.exit(1)

    # 3. Load Cleaned Documents
    docs_to_chunk = []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        doc = Document.from_json(line.strip())
                        docs_to_chunk.append(doc)
                    except Exception as e:
                        logger.warning(f"Skipping invalid JSON line: {e}")
        
        print(f"Loaded {len(docs_to_chunk)} cleaned documents.")

    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        sys.exit(1)

    # 4. Run Chunking Logic
    try:
        chunker = SOPChunker()
        nodes = chunker.chunk_documents(docs_to_chunk)
    except Exception as e:
        logger.error(f"Critical Error during chunking: {e}")
        sys.exit(1)

    # 5. Save Output (Nodes)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for node in nodes:
                # Nodes in LlamaIndex verify strictly, using .to_json() is safest
                f.write(node.to_json() + "\n")
        
        print(f"Success! Saved {len(nodes)} chunks to: {OUTPUT_FILE}")

        # 6. Preview / Validation
        if nodes:
            first_node = nodes[0]
            print("\n--- Context Injection Check (First Chunk) ---")
            print(f"Chunk ID: {first_node.node_id}")
            print(f"Metadata Header Path: {first_node.metadata.get('context_header', 'N/A')}")
            print("-" * 40)
            # Print the first 400 chars to verify the "CONTEXT: ..." string was added
            print(first_node.text[:400])
            print("..." if len(first_node.text) > 400 else "")
            print("-" * 40)

    except Exception as e:
        logger.error(f"Failed to write output file: {e}")