import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class VersionManager:
    """
    Metadata Extractor & Version Controller.
    
    Responsibilities:
    1. Sanitize messy filenames (timestamps, OS duplicates).
    2. Extract clean SOP Titles and Version Numbers.
    3. Normalize versions for mathematical comparison.
    """

    # 1. Regex for the timestamps appended to file extensions (e.g., .pdfNov302025024051)
    TIMESTAMP_SUFFIX_PATTERN = re.compile(r"[A-Za-z]{3}\d{10,}$")
    # 2. Regex for explicit versioning (e.g., v1.0, Rev03, ver-5)
    EXPLICIT_VERSION_PATTERN = re.compile(r"[\-_ ](v|ver|rev|version)[\.\-_]?(\d+(\.\d+)*)", re.IGNORECASE)
    # 3. Regex for implicit ID-based versioning (e.g., ...0002-01 -> Version 01)
    IMPLICIT_ID_PATTERN = re.compile(r"[\-_](\d{2,3})$")
    # 4. Regex for OS duplicates: " (1)", " (1) 1", " (2)"
    DUPLICATE_PATTERN = re.compile(r"\s*\(\d+\)(\s*\d+)?")

    @staticmethod
    def _normalize_version(version_str: str) -> float:
        """
        Converts string versions ('02', '1.5', 'Rev06') to floats for comparison.
        Used to determine which file is newer.
        """
        try:
            # Remove non-numeric characters except dots
            clean = re.sub(r"[^\d\.]", "", version_str)
            return float(clean)
        except ValueError:
            logger.warning(f"Could not normalize version '{version_str}'. Defaulting to 0.0")
            return 0.0

    @staticmethod
    def _clean_stem(filename: str) -> str:
        """
        Aggressively cleans the filename before processing.
        Handles the 'pdfNov30...' artifacts from the screenshot.
        """
        # 1. Strip the weird timestamp suffix first if present, 'AT-GE...01.pdfNov302025...' -> 'AT-GE...01.pdf'
        clean_name = re.sub(VersionManager.TIMESTAMP_SUFFIX_PATTERN, "", filename)
        # 2. Now use Path logic to get the stem (removes .pdf, .docx)
        stem = Path(clean_name).stem
        # 3. Remove OS duplicates like " (1)"
        stem = re.sub(VersionManager.DUPLICATE_PATTERN, "", stem)
        return stem.strip()

    @classmethod
    def extract_metadata(cls, file_path: str) -> Dict[str, Any]:
        """
        Main entry point. Analyzes filename to extract Title and Version.
        
        Returns:
            Dict containing: sop_title, version_str, version_float, original_file
        """
        path_obj = Path(file_path)
        original_filename = path_obj.name
        
        # Step 1: Get the clean base name (No extension, no timestamps, no (1))
        clean_stem = cls._clean_stem(original_filename)
        title = clean_stem
        version_str = "1.0" # Default fallback
        # Step 2: Try Explicit Matching (Rev06, V5)
        match_explicit = cls.EXPLICIT_VERSION_PATTERN.search(clean_stem)
        
        if match_explicit:
            version_str = match_explicit.group(2)
            title = clean_stem[:match_explicit.start()]
        else:
            # Step 3: Try Implicit ID Matching (The -01 at end of IDs)
            match_implicit = cls.IMPLICIT_ID_PATTERN.search(clean_stem)
            if match_implicit:
                version_str = match_implicit.group(1)
                title = clean_stem[:match_implicit.start()]

        # Step 4: Final Polish of Title
        final_title = title.strip()
        # Step 5: Normalize version for DB sorting
        version_float = cls._normalize_version(version_str)

        return {
            "sop_title": final_title,
            "version_original": version_str,
            "version_float": version_float,
            "file_name": original_filename,
            "file_path": str(file_path)
        }
    



if __name__ == "__main__":
    print("--- FASA Version Manager: Diagnostic Test ---\n")
    test_files = [
        "data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051",
        "data/raw_sops/GL-QA-094-A020-01.pdfNov302025024136",
        "data/raw_sops/GRT_PROC_English_stamped_Rev06.docx",
        "data/raw_sops/GRT_PROC_Italian_stamped_Rev04 (1).docx",
        "data/raw_sops/SOP-Manufacturing-Safety_v2.5.pdf",
        "data/raw_sops/General_Policy_Draft.txt"
    ]

    print(f"{'ORIGINAL FILENAME':<55} | {'CLEAN TITLE':<30} | {'VER (STR)':<10} | {'VER (FLOAT)'}")
    print("-" * 115)
    for file_path in test_files:
        try:
            # Run the extraction logic
            meta = VersionManager.extract_metadata(file_path)
            # Print row
            print(f"{Path(file_path).name:<55} | {meta['sop_title']:<30} | {meta['version_original']:<10} | {meta['version_float']}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
    print("\n--- Logic Validation ---")
    
    # 2. validate the 'Strict Version Control' logic
    v1_file = "GRT_PROC_English_stamped_Rev06.docx"
    v2_file = "GRT_PROC_English_stamped_Rev07.docx"
    
    meta_v1 = VersionManager.extract_metadata(v1_file)
    meta_v2 = VersionManager.extract_metadata(v2_file)
    
    print(f"Comparing '{v1_file}' vs '{v2_file}':")
    if meta_v2['version_float'] > meta_v1['version_float']:
        print(f"SUCCESS: System correctly identifies Rev07 ({meta_v2['version_float']}) is newer than Rev06 ({meta_v1['version_float']}).")
        print("Action: Old index would be deleted.") 
    else:
        print("FAIL: Version comparison logic failed.")