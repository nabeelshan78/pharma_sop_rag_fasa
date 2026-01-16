import fitz  # PyMuPDF
import os
from typing import List

from llama_index.core.schema import TextNode
from .cleaner import clean_text
# ---------------------------------------------------------
# CHANGE 1: Import the new function
# ---------------------------------------------------------
from .versioning import VersionManager

class PDFLoader:
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalizes text for consistent logic checking."""
        if not text: return ""
        return " ".join(text.lower().split())

    @staticmethod
    def load_pdf(pdf_path: str) -> List[TextNode]:
        if not os.path.exists(pdf_path):
            print(f"File not found: {pdf_path}")
            return []

        file_name = os.path.basename(pdf_path)
        print(f"Processing PDF: {file_name}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"Failed to open PDF {file_name}: {e}")
            return []
        
        page_nodes = []
        
        # ---------------------------------------------------------
        # CHANGE 2: Extract Metadata from Page 0 before looping
        # ---------------------------------------------------------
        # A. Extract raw text from the first page (Cover Page)
        first_page_text = ""
        if len(doc) > 0:
            first_page_text = doc[0].get_text("text")
            
        # B. Run your new extraction function
        sop_meta = VersionManager.extract_sop_metadata(first_page_text)
        
        # C. Determine Title: Use extracted title if found, otherwise fallback to filename
        sop_title = sop_meta.get("document_title") or file_name.replace(".pdf", "").replace("_", " ")
        # ---------------------------------------------------------

        for i, page in enumerate(doc):
            if i == 0: continue 
            
            # 1. Get Original Raw Text
            raw_text = page.get_text("text")
            
            # 2. Logic Check (using normalized view)
            logic_view = PDFLoader._normalize_text(raw_text)
            if "standard operating procedure" in logic_view or "table of contents" in logic_view:
                continue

            # 3. Handle Historical Index Slicing
            if "historical index" in logic_view:
                lower_raw = raw_text.lower()
                index_pos = lower_raw.find("historical index")
                if index_pos != -1:
                    raw_text = raw_text[:index_pos]

            # 4. Clean the ORIGINAL text
            cleaned_original = clean_text(raw_text)
            if not cleaned_original:
                continue
            
            text_for_storage = cleaned_original.lower()            
            page_label = f"Page {i + 1}"
            annotated_original = f"Source: {file_name}, {page_label}.\n{cleaned_original}"
            
            # C. Create Node (Now with extra metadata!)
            node = TextNode(
                text=text_for_storage,
                metadata={
                    "file_name": file_name,
                    "page_label": page_label,
                    "sop_title": sop_title,
                    "original_text": annotated_original,
                    "document_number": sop_meta.get("document_number", "Unknown"),
                    "version_number": sop_meta.get("version_number", "Unknown"),
                    "status": "Active"
                }
            )
                    
            node.excluded_embed_metadata_keys = ["original_text"]
            node.excluded_llm_metadata_keys = ["original_text"]

            page_nodes.append(node)
        
        doc.close()
        return page_nodes
    



