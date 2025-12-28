import fitz  # PyMuPDF
import os
import re
import logging
from typing import List, Optional

from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SentenceSplitter

try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# =========================================================================================

class PDFProcessor:
    """
    Handles PDF Loading, Cleaning, and Chunking into LlamaIndex Nodes.
    """

    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def _clean_text(self, text: str) -> str:
        """
        Applies Regex cleaning rules to remove noise (headers, footers).
        """
        # 1. HEADER REMOVAL (Generic SOP headers)
        header_keywords = [
            r"Number:.*", 
            r"Revision:.*", 
            r"Status:.*", 
            r"Effective Date:.*",
            r"Document No:.*"
        ]
        for pattern in header_keywords:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        # 2. FOOTER CUTOFF (Grünenthal specific & Generic)
        # Anything after "This is an uncontrolled copy" is usually legal footer noise
        footer_patterns = [
            r"(This is an uncontrolled copy valid for.*)",
            r"(Page \d+ of \d+)"
        ]
        for pattern in footer_patterns:
            match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
            if match:
                # Cut everything after the match start
                text = text[:match.start()]

        # 3. PAGINATION REMOVAL (Isolated numbers like "1 of 10")
        text = re.sub(r"\b\d+\s+of\s+\d+\b", "", text)

        # 4. WHITESPACE CLEANUP (Collapse multiple newlines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def process_pdf(self, pdf_path: str) -> List[TextNode]:
        """
        Main pipeline: Load PDF -> Extract -> Clean -> Chunk -> Return Nodes.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"File not found: {pdf_path}")
            return []

        file_name = os.path.basename(pdf_path)
        logger.info(f"Processing PDF: {file_name}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {file_name}: {e}")
            return []
        
        all_nodes = []
        
        # --- PHASE 1: EXTRACTION ---
        full_doc_text = ""
        page_texts = []

        # We try to guess the Title from the first page (common in SOPs)
        sop_title = file_name.replace(".pdf", "").replace("_", " ")

        for i, page in enumerate(doc):
            # Skip Cover Page if it's just a title wrapper (Optional: adjust as needed)
            # if i == 0: continue 

            raw_text = page.get_text("text")
            cleaned_text = self._clean_text(raw_text)

            if not cleaned_text:
                continue

            # Context Injection: Add Source metadata directly into text for the LLM
            # This helps the LLM cite sources accurately.
            page_label = f"Page {i + 1}"
            annotated_text = f"Source: {file_name}, {page_label}.\n{cleaned_text}"
            
            # We store the raw text to pass to the splitter
            # Note: We pass Metadata separately to the Node
            page_node = TextNode(
                text=annotated_text,
                metadata={
                    "file_name": file_name,
                    "page_label": page_label,
                    "sop_title": sop_title,
                }
            )
            page_texts.append(page_node)

        doc.close()
        logger.info(f"Extracted {len(page_texts)} valid pages from {file_name}")

        # --- PHASE 2: CHUNKING ---
        # LlamaIndex splitter takes text and returns TextNodes (chunks)
        # get_nodes_from_documents handles the splitting while preserving metadata
        final_nodes = self.splitter.get_nodes_from_documents(page_texts)

        logger.info(f"Generated {len(final_nodes)} chunks for Vector DB.")
        return final_nodes







# --- SELF TEST ---
if __name__ == "__main__":
    # Define your test file path here
    # INPUT_PDF = "data/raw_sops/your_test_file.pdf"
    
    # Create a dummy file for testing if one doesn't exist
    INPUT_PDF = "test_sop.pdf"
    if not os.path.exists(INPUT_PDF):
        with open(INPUT_PDF, "w") as f: f.write("dummy content") # Just to prevent error in logic check

    processor = PDFProcessor()
    nodes = processor.process_pdf(INPUT_PDF)

    if nodes:
        print("\n--- DIAGNOSTIC RESULT ---")
        print(f"Total Nodes Created: {len(nodes)}")
        print(f"Sample Node 1 Metadata: {nodes[0].metadata}")
        print(f"Sample Node 1 Text Preview:\n{nodes[0].text[:200]}...")