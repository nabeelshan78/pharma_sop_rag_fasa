import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Setup local logger
logger = logging.getLogger(__name__)

class VersionManager:
    """
    Enterprise Metadata Extractor & Version Controller.
    
    Responsibilities:
    1. Sanitize messy filenames (timestamps, OS duplicates).
    2. Extract clean SOP Titles and Version Numbers.
    3. Normalize versions for mathematical comparison (Phase 2 Requirement).
    """

    # 1. Regex for the timestamps seen in your screenshot (e.g., Nov302025024051)
    # Matches Month(3 chars) + Day/Year/Time digits at the end of a string
    TIMESTAMP_SUFFIX_PATTERN = re.compile(r"[A-Za-z]{3}\d{10,}$")

    # 2. Regex for explicit versioning (e.g., v1.0, Rev03, ver-5)
    EXPLICIT_VERSION_PATTERN = re.compile(r"[\-_ ](v|ver|rev|version)[\.\-_]?(\d+(\.\d+)*)", re.IGNORECASE)

    # 3. Regex for implicit ID-based versioning (e.g., ...0002-01 -> Version 01)
    # Logic: End of string, hyphen, 2-3 digits. 
    IMPLICIT_ID_PATTERN = re.compile(r"[\-_](\d{2,3})$")

    # 4. Regex for OS duplicates: " (1)", " (1) 1", " (2)"
    DUPLICATE_PATTERN = re.compile(r"\s*\(\d+\)(\s*\d+)?")

    # 5. Noise words to strip from Title to improve vector search quality
    # We remove 'stamped' as seen in your image, as it denotes status, not content.
    NOISE_WORDS = ["stamped", "signed", "draft", "final", "english", "italian", "copy"]

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
        # 1. Strip the weird timestamp suffix first if present
        # This handles 'AT-GE...01.pdfNov302025...' -> 'AT-GE...01.pdf'
        clean_name = re.sub(VersionManager.TIMESTAMP_SUFFIX_PATTERN, "", filename)
        
        # 2. Now use Path logic to get the stem (removes .pdf, .docx)
        stem = Path(clean_name).stem

        # 3. Remove OS duplicates like " (1)"
        stem = re.sub(VersionManager.DUPLICATE_PATTERN, "", stem)
        
        return stem.strip()

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        """
        Removes underscores and noise words to create a clean, searchable title.
        """
        # Replace separators with spaces
        title = raw_title.replace("_", " ").replace("-", " ")
        
        # Remove noise words (case insensitive)
        tokens = title.split()
        clean_tokens = [t for t in tokens if t.lower() not in VersionManager.NOISE_WORDS]
        
        return " ".join(clean_tokens).strip()

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
            # Title is everything before the match
            title = clean_stem[:match_explicit.start()]
            
        else:
            # Step 3: Try Implicit ID Matching (The -01 at end of IDs)
            match_implicit = cls.IMPLICIT_ID_PATTERN.search(clean_stem)
            
            if match_implicit:
                version_str = match_implicit.group(1)
                # Title is the part before the version
                title = clean_stem[:match_implicit.start()]

        # Step 4: Final Polish of Title
        final_title = cls._clean_title(title)
        
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
    # Configure basic logging for the test
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    print("--- FASA Version Manager: Diagnostic Test ---\n")

    # 1. Simulate the messy file list based on your screenshot and common edge cases
    test_files = [
        # The specific nightmare case from your image (Timestamp appended to extension)
        "data/raw_sops/AT-GE-577-0002-01.pdfNov302025024051",
        
        # Another timestamp case from image
        "data/raw_sops/GL-QA-094-A020-01.pdfNov302025024136",
        
        # Explicit version with noise words ("English", "stamped")
        "data/raw_sops/GRT_PROC_English_stamped_Rev06.docx",
        
        # OS Duplicate artifact "(1)"
        "data/raw_sops/GRT_PROC_Italian_stamped_Rev04 (1).docx",
        
        # Standard clean case
        "data/raw_sops/SOP-Manufacturing-Safety_v2.5.pdf",
        
        # No version detected (Fallback case)
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
    
    # 2. validate the 'Strict Version Control' logic (Phase 1 Req B & Source 8)
    # proving we can mathematically compare versions now.
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




# import re
# from pathlib import Path
# from typing import Dict, Any, Tuple
# import logging

# # Setup local logger
# logger = logging.getLogger(__name__)

# class VersionManager:
#     """
#     Robust Metadata Extractor for Pharma SOPs.
#     Handles messy filenames, export timestamps, OS duplicates, and various versioning styles.
#     """

#     # 1. Regex to find explicit versioning (e.g., v1.0, Rev03, ver-5)
#     # Looks for v, ver, rev (case insensitive) followed by digits
#     EXPLICIT_VERSION_PATTERN = re.compile(r"[\-_ ](v|ver|rev|version)[\.\-_]?(\d+(\.\d+)*)", re.IGNORECASE)

#     # 2. Regex to find implicit ID-based versioning (e.g., SOP-001-02 -> Version 02)
#     # Matches a hyphen/underscore followed by 2-3 digits at the very end of the string
#     IMPLICIT_ID_PATTERN = re.compile(r"[\-_](\d{2,3})$")

#     # 3. Regex to clean OS duplicate artifacts like " (1)", " (2)"
#     DUPLICATE_PATTERN = re.compile(r"\s*\(\d+\)(\s*\d+)?")

#     @staticmethod
#     def _clean_stem(filename: str) -> str:
#         """
#         Removes file extension noise and OS duplication artifacts.
#         Ex: "SOP_v1 (1).pdfNov30..." -> "SOP_v1"
#         """
#         # Remove known "bad" extensions or timestamp suffixes if they exist
#         # We assume the actual stem ends before the first dot, or we parse carefully.
#         path_obj = Path(filename)
        
#         # Handle cases like .pdfNov302025... by taking the stem strictly
#         stem = path_obj.stem

#         # Remove OS duplicates like " (1)" or " (1) 1"
#         clean_stem = re.sub(VersionManager.DUPLICATE_PATTERN, "", stem)
#         return clean_stem.strip()

#     @staticmethod
#     def extract_metadata(file_path: str) -> Dict[str, Any]:
#         """
#         Analyzes the filename to extract a clean Title and Version.
#         """
#         path_obj = Path(file_path)
#         original_filename = path_obj.name
        
#         # Step 1: Clean the filename of noise
#         clean_stem = VersionManager._clean_stem(original_filename)
        
#         title = clean_stem
#         version_str = "1.0" # Default fallback
#         extraction_method = "default"

#         # Step 2: Try Explicit Matching (Rev06, V5, etc.)
#         match_explicit = VersionManager.EXPLICIT_VERSION_PATTERN.search(clean_stem)
        
#         if match_explicit:
#             # Group 1 is (v/rev), Group 2 is the number (06, 5, 1.2)
#             version_str = match_explicit.group(2)
#             # Title is everything before the match
#             title = clean_stem[:match_explicit.start()].strip(" -_")
#             extraction_method = "explicit_pattern"
            
#         else:
#             # Step 3: Try Implicit ID Matching (The -01 at end of IDs)
#             # Useful for files like: AT-GE-577-0002-01
#             match_implicit = VersionManager.IMPLICIT_ID_PATTERN.search(clean_stem)
            
#             if match_implicit:
#                 version_str = match_implicit.group(1)
#                 # Title is the ID part before the version
#                 title = clean_stem[:match_implicit.start()].strip(" -_")

#         # Step 4: Final Cleanup of Title
#         # Replace remaining underscores with spaces for better embedding search
#         clean_title = title.replace("_", " ").strip()

#         return {
#             "sop_title": clean_title,
#             "version": version_str,
#             "file_path": str(file_path)
#         }



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