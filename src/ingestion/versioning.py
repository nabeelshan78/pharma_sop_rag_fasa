import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class VersionManager:
    """
    Metadata Extractor & Version Controller.
    """

    TIMESTAMP_SUFFIX_PATTERN = re.compile(r"[A-Za-z]{3}\d{10,}$")
    EXPLICIT_VERSION_PATTERN = re.compile(r"[\-_ ](v|ver|rev|version)[\.\-_]?(\d+(\.\d+)*)", re.IGNORECASE)
    IMPLICIT_ID_PATTERN = re.compile(r"[\-_](\d{2,3})$")
    DUPLICATE_PATTERN = re.compile(r"\s*\(\d+\)(\s*\d+)?")


    @staticmethod
    def extract_sop_metadata(text: str) -> dict:
        """
        Parses the first page text to extract specific SOP metadata using 
        pattern anchors (PROC-ID, Status) because labels are often disconnected.
        """
        metadata = {
            "document_number": "Unknown",
            "document_title": "Unknown",
            "revision_number": "Unknown"
        }
        
        if not text:
            return metadata

        # 1. Extract Document Number (Anchor: starts with PROC-)
        # We look for PROC- followed by digits
        proc_match = re.search(r"(PROC-\d+)", text)
        if proc_match:
            metadata["document_number"] = proc_match.group(1).strip()
            
            # 2. Extract Title (Strategy: Text immediately AFTER the PROC number)
            # We find where PROC-XXXX ends, and take the next non-empty lines
            start_index = proc_match.end()
            # Get the text chunk after the number
            remaining_text = text[start_index:]
            # Split by lines and take the first non-empty line as the title
            lines = [line.strip() for line in remaining_text.splitlines() if line.strip()]
            if lines:
                # Sometimes the title is repeated or split, taking the first valid line is usually safe
                metadata["document_title"] = lines[0]

        # 3. Extract Revision (Anchor: Look for 'Release' or 'Draft')
        # The revision (e.g., '01', '03') always appears right BEFORE the Status words.
        # We look for 1-2 digits, followed by optional whitespace/newlines, followed by Release or Draft
        rev_match = re.search(r"(\d{1,2})\s+(?:Release|Draft)", text, re.MULTILINE)
        if rev_match:
            metadata["version_number"] = rev_match.group(1).strip()

        return metadata

    @staticmethod
    def _normalize_version(version_str: str) -> float:
        try:
            clean = re.sub(r"[^\d\.]", "", version_str)
            return float(clean)
        except ValueError:
            logger.warning(f"Could not normalize version '{version_str}'. Defaulting to 0.0")
            return 0.0

    @staticmethod
    def _clean_stem(filename: str) -> str:
        clean_name = re.sub(VersionManager.TIMESTAMP_SUFFIX_PATTERN, "", filename)
        stem = Path(clean_name).stem
        stem = re.sub(VersionManager.DUPLICATE_PATTERN, "", stem)
        return stem.strip()

    @classmethod
    def extract_metadata(cls, file_path: str) -> Dict[str, Any]:
        """
        Main entry point.
        """
        path_obj = Path(file_path)
        original_filename = path_obj.name
        
        clean_stem = cls._clean_stem(original_filename)
        title = clean_stem
        version_str = "1.0" # Default fallback
        match_explicit = cls.EXPLICIT_VERSION_PATTERN.search(clean_stem)
        
        if match_explicit:
            version_str = match_explicit.group(2)
            title = clean_stem[:match_explicit.start()]
        else:
            match_implicit = cls.IMPLICIT_ID_PATTERN.search(clean_stem)
            if match_implicit:
                version_str = match_implicit.group(1)
                title = clean_stem[:match_implicit.start()]

        final_title = title.strip()
        version_float = cls._normalize_version(version_str)

        return {
            "sop_title": final_title,
            "version_original": version_str,
            "version_float": version_float,
            "file_name": original_filename,
            "file_path": str(file_path)
        }
    










# ... (Keep your extract_sop_metadata function above this) ...

if __name__ == "__main__":
    import os
    import fitz

    # Define path to your data directory (2 levels up)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sops_dir = os.path.abspath(os.path.join(base_dir, "../../data/raw_sops"))

    print(f"🔍 Scanning directory: {sops_dir}\n")

    if not os.path.exists(sops_dir):
        print("❌ Directory not found! Check your path.")
    else:
        # Loop through all files in the folder
        for filename in os.listdir(sops_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(sops_dir, filename)
                
                try:
                    # Open PDF and get text from FIRST page only
                    doc = fitz.open(pdf_path)
                    if len(doc) > 0:
                        first_page_text = doc[0].get_text("text")
                        # print(f"First page text extracted: {first_page_text}")
                        
                        # TEST THE FUNCTION
                        extracted_data = VersionManager.extract_sop_metadata(first_page_text)
                        
                        print(f"📄 File: {filename}")
                        print(f"   ├─ Number:   {extracted_data['document_number']}")
                        print(f"   ├─ Title:    {extracted_data['document_title']}")
                        print(f"   └─ Revision: {extracted_data['revision_number']}")
                        print("=" * 100)
                    
                    doc.close()
                except Exception as e:
                    print(f"⚠️ Error reading {filename}: {e}")









# if __name__ == "__main__":
#     print("--- FASA Version Manager: Diagnostic Test ---\n")

#     meta = VersionManager.extract_metadata("data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051")
#     print(meta)
    
#     test_files = [
#         "data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051",
#         "data/raw_sops/GL-QA-094-A020-01.pdfNov302025024136",
#         "data/raw_sops/GRT_PROC_English_stamped_Rev06.docx",
#         "data/raw_sops/GRT_PROC_Italian_stamped_Rev04 (1).docx",
#         "data/raw_sops/SOP-Manufacturing-Safety_v2.5.pdf",
#         "data/raw_sops/General_Policy_Draft.txt"
#     ]

#     print(f"{'ORIGINAL FILENAME':<55} | {'CLEAN TITLE':<30} | {'VER (STR)':<10} | {'VER (FLOAT)'}")
#     print("-" * 115)
#     for file_path in test_files:
#         try:
#             # Run the extraction logic
#             meta = VersionManager.extract_metadata(file_path)
#             # Print row
#             print(f"{Path(file_path).name:<55} | {meta['sop_title']:<30} | {meta['version_original']:<10} | {meta['version_float']}")
#         except Exception as e:
#             logger.error(f"Failed to process {file_path}: {e}")
#     print("\n--- Logic Validation ---")
    
#     # 2. validate the 'Strict Version Control' logic
#     v1_file = "GRT_PROC_English_stamped_Rev06.docx"
#     v2_file = "GRT_PROC_English_stamped_Rev07.docx"
    
#     meta_v1 = VersionManager.extract_metadata(v1_file)
#     meta_v2 = VersionManager.extract_metadata(v2_file)
    
#     print(f"Comparing '{v1_file}' vs '{v2_file}':")
#     if meta_v2['version_float'] > meta_v1['version_float']:
#         print(f"SUCCESS: System correctly identifies Rev07 ({meta_v2['version_float']}) is newer than Rev06 ({meta_v1['version_float']}).")
#         print("Action: Old index would be deleted.") 
#     else:
#         print("FAIL: Version comparison logic failed.")