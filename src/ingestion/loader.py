import fitz  # PyMuPDF
import os
from typing import List

from llama_index.core.schema import TextNode
from .cleaner import clean_text
# ---------------------------------------------------------
# CHANGE 1: Import the new function
# ---------------------------------------------------------
from .versioning import VersionManager




import fitz  # PyMuPDF
from langdetect import detect, DetectorFactory, LangDetectException
import os

# CRITICAL: Set seed for consistent results
DetectorFactory.seed = 0 

def detect_language(sample_text):
    # Detect
    detected_lang = "unknown"
    try:
        if len(sample_text.strip()) > 50:
            detected_lang = detect(sample_text) 
        else:
            detected_lang = "en" 
    except LangDetectException:
        detected_lang = "unknown"
    return detected_lang



class PDFLoader:
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalizes text for consistent logic checking."""
        if not text: return ""
        return " ".join(text.lower().split())


    # =========================================================================
    # LANGUAGE SPECIFIC PROCESSORS
    # Use these to customize cleaning/filtering for each language later
    # =========================================================================

    @staticmethod
    def _process_english_pages(doc, file_name, sop_meta) -> List[TextNode]:
        page_nodes = []
        for i, page in enumerate(doc):
            if i == 0: continue # Skip cover
            
            raw_text = page.get_text("text")
            logic_view = PDFLoader._normalize_text(raw_text)

            # English specific filtering
            if "standard operating procedure" in logic_view or "table of contents" in logic_view:
                continue

            # English specific slicing
            if "historical index" in logic_view:
                lower_raw = raw_text.lower()
                index_pos = lower_raw.find("historical index")
                if index_pos != -1:
                    raw_text = raw_text[:index_pos]

            # TODO: Call English-specific cleaner here later
            cleaned_original = clean_text(raw_text) 
            if not cleaned_original: continue
            
            PDFLoader._create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta)
        return page_nodes

    @staticmethod
    def _process_german_pages(doc, file_name, sop_meta) -> List[TextNode]:
        page_nodes = []
        for i, page in enumerate(doc):
            if i == 0: continue 
            
            raw_text = page.get_text("text")
            logic_view = PDFLoader._normalize_text(raw_text)

            # German Specific Filtering
            # "standardarbeitsanweisung" = SOP, "inhaltsverzeichnis" = Table of Contents
            if "standardarbeitsanweisung" in logic_view or "inhaltsverzeichnis" in logic_view:
                continue

            # German Index Slicing HISTORIENINDEX ---> small = historienindex
            # Checks for "historischer index" OR "änderungshistorie" (common in pharma)
            if "historienindex" in logic_view:
                lower_raw = raw_text.lower()
                idx_pos = lower_raw.find("historienindex")
                if idx_pos != -1:
                    raw_text = raw_text[:idx_pos]

            # TODO: Call German-specific cleaner here later
            cleaned_original = clean_text(raw_text)
            if not cleaned_original: continue

            PDFLoader._create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta)
        return page_nodes

    @staticmethod
    def _process_italian_pages(doc, file_name, sop_meta) -> List[TextNode]:
        page_nodes = []
        for i, page in enumerate(doc):
            if i == 0: continue 
            
            raw_text = page.get_text("text")
            logic_view = PDFLoader._normalize_text(raw_text)

            # Italian Specific Filtering
            # "procedura operativa standard" = SOP, "sommario"/"indice" = Table of Contents
            if "procedura operativa standard" in logic_view or "sommario" in logic_view or "indice dei contenuti" in logic_view:
                continue

            # Italian Index Slicing
            if "indice storico" in logic_view:
                lower_raw = raw_text.lower()
                idx_pos = lower_raw.find("indice storico")
                if idx_pos != -1:
                    raw_text = raw_text[:idx_pos]

            cleaned_original = clean_text(raw_text)
            if not cleaned_original: continue

            PDFLoader._create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta)
        return page_nodes

    @staticmethod
    def _process_portuguese_pages(doc, file_name, sop_meta) -> List[TextNode]:
        page_nodes = []
        for i, page in enumerate(doc):
            if i == 0: continue 
            
            raw_text = page.get_text("text")
            logic_view = PDFLoader._normalize_text(raw_text)

            # Portuguese Specific Filtering
            # "procedimento operacional padrão" = SOP, "índice"/"sumário" = Table of Contents
            if "procedimento operacional padrão" in logic_view or "índice" in logic_view or "sumário" in logic_view:
                continue

            # Portuguese Index Slicing
            if "histórico" in logic_view:
                lower_raw = raw_text.lower()
                idx_pos = lower_raw.find("histórico")
                if idx_pos != -1:
                    raw_text = raw_text[:idx_pos]

            cleaned_original = clean_text(raw_text)
            if not cleaned_original: continue

            PDFLoader._create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta)
        return page_nodes

    @staticmethod
    def _process_spanish_pages(doc, file_name, sop_meta) -> List[TextNode]:
        page_nodes = []
        for i, page in enumerate(doc):
            if i == 0: continue 
            
            raw_text = page.get_text("text")
            logic_view = PDFLoader._normalize_text(raw_text)

            # Spanish Specific Filtering
            # "procedimiento operativo estándar" = SOP, "tabla de contenidos" = Table of Contents
            if "procedimiento operativo estándar" in logic_view or "contenido" in logic_view:
                continue

            # Spanish Index Slicing
            if "historial de cambios" in logic_view:
                lower_raw = raw_text.lower()
                idx_pos = lower_raw.find("historial de cambios")
                if idx_pos != -1:
                    raw_text = raw_text[:idx_pos]

            cleaned_original = clean_text(raw_text)
            if not cleaned_original: continue

            PDFLoader._create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta)
        return page_nodes
    

    # =========================================================================
    # SHARED HELPERS
    # =========================================================================

    @staticmethod
    def _create_and_append_node(page_nodes, cleaned_original, i, file_name, sop_meta):
        """Helper to create node and append to list to avoid code duplication."""
        text_for_storage = cleaned_original.lower()            
        page_label = f"Page {i + 1}"
        annotated_original = f"Source: {file_name}, {page_label}.\n{cleaned_original}"
        
        node = TextNode(
            text=text_for_storage,
            metadata={
                "file_name": file_name,
                "page_label": page_label,
                "sop_title": sop_meta.get("document_title") or file_name.replace(".pdf", "").replace("_", " "),
                "original_text": annotated_original,
                "document_number": sop_meta.get("document_number", "Unknown"),
                "version_number": sop_meta.get("version_number", "Unknown"),
                "status": "Active",                
                "language": sop_meta.get("language", "unknown") 
            }
        )
                
        node.excluded_embed_metadata_keys = ["original_text"]
        node.excluded_llm_metadata_keys = ["original_text"]
        page_nodes.append(node)

    # =========================================================================
    # MAIN LOAD FUNCTION
    # =========================================================================

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
        
        # 1. Detect Language from Page 2 & 3
        sample_text = ""
        for p_idx in [1, 2]:
            sample_text += doc[p_idx].get_text()

        detected_language = detect_language(sample_text)
        print(f"  > Detected Language: {detected_language}")
        
        # 2. Extract Metadata from Page 1 (Index 0)
        first_page_text = ""
        if len(doc) > 0:
            first_page_text = doc[0].get_text("text")
            
        sop_meta = VersionManager.extract_sop_metadata(first_page_text)
        # Inject detected language into metadata for tracking
        sop_meta["language"] = detected_language

        # 3. Dispatch to Language Specific Processors
        if detected_language == 'en':
            return PDFLoader._process_english_pages(doc, file_name, sop_meta)
        elif detected_language == 'de':
            return PDFLoader._process_german_pages(doc, file_name, sop_meta)
        elif detected_language == 'it':
            return PDFLoader._process_italian_pages(doc, file_name, sop_meta)
        elif detected_language == 'pt':
            return PDFLoader._process_portuguese_pages(doc, file_name, sop_meta)
        elif detected_language == 'es':
            return PDFLoader._process_spanish_pages(doc, file_name, sop_meta)
        else:
            print(f"  > Warning: Language '{detected_language}' not explicitly handled.")