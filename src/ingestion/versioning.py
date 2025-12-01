import re
from pathlib import Path
from typing import Dict, Any, Tuple
import logging

# Setup local logger
logger = logging.getLogger(__name__)

class VersionManager:
    """
    Robust Metadata Extractor for Pharma SOPs.
    Handles messy filenames, export timestamps, OS duplicates, and various versioning styles.
    """

    # 1. Regex to find explicit versioning (e.g., v1.0, Rev03, ver-5)
    # Looks for v, ver, rev (case insensitive) followed by digits
    EXPLICIT_VERSION_PATTERN = re.compile(r"[\-_ ](v|ver|rev|version)[\.\-_]?(\d+(\.\d+)*)", re.IGNORECASE)

    # 2. Regex to find implicit ID-based versioning (e.g., SOP-001-02 -> Version 02)
    # Matches a hyphen/underscore followed by 2-3 digits at the very end of the string
    IMPLICIT_ID_PATTERN = re.compile(r"[\-_](\d{2,3})$")

    # 3. Regex to clean OS duplicate artifacts like " (1)", " (2)"
    DUPLICATE_PATTERN = re.compile(r"\s*\(\d+\)(\s*\d+)?")

    @staticmethod
    def _clean_stem(filename: str) -> str:
        """
        Removes file extension noise and OS duplication artifacts.
        Ex: "SOP_v1 (1).pdfNov30..." -> "SOP_v1"
        """
        # Remove known "bad" extensions or timestamp suffixes if they exist
        # We assume the actual stem ends before the first dot, or we parse carefully.
        path_obj = Path(filename)
        
        # Handle cases like .pdfNov302025... by taking the stem strictly
        stem = path_obj.stem

        # Remove OS duplicates like " (1)" or " (1) 1"
        clean_stem = re.sub(VersionManager.DUPLICATE_PATTERN, "", stem)
        return clean_stem.strip()

    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        """
        Analyzes the filename to extract a clean Title and Version.
        """
        path_obj = Path(file_path)
        original_filename = path_obj.name
        
        # Step 1: Clean the filename of noise
        clean_stem = VersionManager._clean_stem(original_filename)
        
        title = clean_stem
        version_str = "1.0" # Default fallback
        extraction_method = "default"

        # Step 2: Try Explicit Matching (Rev06, V5, etc.)
        match_explicit = VersionManager.EXPLICIT_VERSION_PATTERN.search(clean_stem)
        
        if match_explicit:
            # Group 1 is (v/rev), Group 2 is the number (06, 5, 1.2)
            version_str = match_explicit.group(2)
            # Title is everything before the match
            title = clean_stem[:match_explicit.start()].strip(" -_")
            extraction_method = "explicit_pattern"
            
        else:
            # Step 3: Try Implicit ID Matching (The -01 at end of IDs)
            # Useful for files like: AT-GE-577-0002-01
            match_implicit = VersionManager.IMPLICIT_ID_PATTERN.search(clean_stem)
            
            if match_implicit:
                version_str = match_implicit.group(1)
                # Title is the ID part before the version
                title = clean_stem[:match_implicit.start()].strip(" -_")

        # Step 4: Final Cleanup of Title
        # Replace remaining underscores with spaces for better embedding search
        clean_title = title.replace("_", " ").strip()

        return {
            "sop_title": clean_title,
            "version": version_str,
            "filename": original_filename,
            "file_path": str(file_path)
        }



# # --- TEST BLOCK (Delete this when putting into production if you want) ---
# if __name__ == "__main__":
#     test_files = [
#         "GRT_PROC_English_stamped_Rev06.doc",
#         "GRT_PROC_English_stamped_V5 (1) 1.doc",  # Complex duplicate
#         "AT-GE-577-0002-01.pdfNov302025024051",   # That messy timestamp one
#         "GL-QA-094-A020-01.pdf",                   # Standard ID format
#         "Simple_SOP_Cleaning.pdf"                  # No version
#     ]
    
#     print(f"{'FILENAME':<45} | {'TITLE':<30} | {'VERSION'}")
#     print("-" * 90)
#     for f in test_files:
#         meta = VersionManager.extract_metadata(f)
#         print(f"{f[:42] + '...':<45} | {meta['sop_title'][:28]:<30} | {meta['version']}")






# # ingestion/versioning.py
# # Role: Extracts metadata and handles the logic for detecting if a file is an update to an existing SOP.

# import re
# from pathlib import Path
# from typing import Dict, Any, Tuple

# class VersionManager:
#     """
#     Handles SOP metadata extraction and version comparison.
#     Enforces naming convention: SOP_Name_vX.Y.pdf
#     """
    
#     # Regex to capture Title and Version (e.g., "Safety_Proc_v1.2.pdf")
#     FILENAME_PATTERN = r"(.*)_v(\d+(\.\d+)?)"

#     @staticmethod
#     def extract_metadata(file_path: str) -> Dict[str, Any]:
#         filename = Path(file_path).name
#         match = re.search(VersionManager.FILENAME_PATTERN, filename)
        
#         if match:
#             title = match.group(1).replace("_", " ").strip()
#             version_str = match.group(2)
#         else:
#             # Fallback for files without versioning
#             title = Path(file_path).stem.replace("_", " ")
#             version_str = "1.0"

#         return {
#             "sop_name": title,
#             "version": version_str,
#             "filename": filename,
#             "file_path": str(file_path)
#         }

#     @staticmethod
#     def is_newer_version(new_ver: str, old_ver: str) -> bool:
#         """
#         Returns True if new_ver > old_ver.
#         """
#         def parse(v): return [int(x) for x in v.split(".")]
#         return parse(new_ver) > parse(old_ver)