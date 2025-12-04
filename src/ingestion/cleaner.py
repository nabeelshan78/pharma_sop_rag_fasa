import re
import logging
from typing import List
from llama_index.core.schema import Document

from src.core.logger import setup_logger
logger = setup_logger(__name__)

class SOPCleaner:
    """
    Cleaner for Pharmaceutical SOPs.
    """

    def __init__(self):
        self.page_num_pattern = re.compile(r'^\s*(?:Page\s+)?\d+\s+of\s+\d+\s*$', re.IGNORECASE)
        self.doc_id_pattern = re.compile(r'^\s*(?:.*?)\b[A-Z0-9]+(?:-[A-Z0-9]+){2,}\s*$', re.IGNORECASE)
        self.ghost_header_pattern = re.compile(r'^#+\s*(?:Page\s+)?\d+\s+of\s+\d+\s*$', re.IGNORECASE)
        self.signature_pattern = re.compile(r'(?:Signature|Approved by|Reviewed by|Prepared by):\s*[_]+', re.IGNORECASE)
        self.separator_pattern = re.compile(r'^\s*[-_*]{3,}\s*$')
        self.sop_start_pattern = re.compile(r'^#+\s*1\.?0?\s+(Objective|Purpose|Scope|Introduction|Aim)', re.IGNORECASE)

    def clean_documents(self, documents: List[Document]) -> List[Document]:
        cleaned_docs = []
        for doc in documents:
            try:
                original_text = doc.text
                if not original_text:
                    continue
                cleaned_text = self._clean_text_content(original_text)
                new_doc = Document(
                    text=cleaned_text,
                    metadata=doc.metadata.copy() if doc.metadata else {}
                )
                new_doc.metadata['is_cleaned'] = True
                cleaned_docs.append(new_doc)
            except Exception as e:
                logger.error(f"Failed to clean document: {e}", exc_info=True)
                cleaned_docs.append(doc)
        return cleaned_docs

    def _clean_text_content(self, text: str) -> str:
        lines = text.split('\n')
        cleaned_lines = []
        in_toc = False

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped: continue 
            if self.page_num_pattern.match(line_stripped): continue
            if self.doc_id_pattern.match(line_stripped): continue
            if self.ghost_header_pattern.match(line_stripped): continue
            if self.separator_pattern.match(line_stripped): continue
            if line_stripped.startswith('|') and line_stripped.endswith('|'):
                content = line_stripped.replace('|', '').replace('-', '').strip()
                if not content or content == ":": 
                    continue
                cells = [c.strip() for c in line_stripped.split('|') if c]
                if len(cells) == 2 and not cells[1]:
                    continue
            if "# Table of contents" in line_stripped or "# Contents" == line_stripped:
                in_toc = True
                continue
            
            if in_toc:
                if line_stripped.startswith('#'):
                    in_toc = False
                else:
                    continue

            cleaned_lines.append(line)
        start_index = 0
        found_start = False
        for i, line in enumerate(cleaned_lines):
            if self.sop_start_pattern.match(line.strip()):
                start_index = i
                found_start = True
                break
        final_lines = cleaned_lines[start_index:] if found_start else cleaned_lines
        text = '\n'.join(final_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()























# # ==========================================
# #  Testing Block (Runnable)
# # ==========================================
# if __name__ == "__main__":
#     raw_messy_text = ""
#     import json
#     with open("test_outputs/debug_docs.jsonl", "r", encoding="utf-8") as f:
#         for line in f:
#             doc = json.loads(line)
#             raw_messy_text = doc.get('text_preview', '')
#             break
    
#     cleaner = SOPCleaner()
#     doc = Document(text=raw_messy_text, metadata={"source": "test"})
    
#     clean_docs = cleaner.clean_documents([doc])
    
#     print("--- AFTER CLEANING (Full) ---")
#     print(clean_docs[0].text)