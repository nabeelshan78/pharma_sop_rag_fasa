# ingestion/versioning.py
# Role: Extracts metadata and handles the logic for detecting if a file is an update to an existing SOP.

import re
from pathlib import Path
from typing import Dict, Any, Tuple

class VersionManager:
    """
    Handles SOP metadata extraction and version comparison.
    Enforces naming convention: SOP_Name_vX.Y.pdf
    """
    
    # Regex to capture Title and Version (e.g., "Safety_Proc_v1.2.pdf")
    FILENAME_PATTERN = r"(.*)_v(\d+(\.\d+)?)"

    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        filename = Path(file_path).name
        match = re.search(VersionManager.FILENAME_PATTERN, filename)
        
        if match:
            title = match.group(1).replace("_", " ").strip()
            version_str = match.group(2)
        else:
            # Fallback for files without versioning
            title = Path(file_path).stem.replace("_", " ")
            version_str = "1.0"

        return {
            "sop_name": title,
            "version": version_str,
            "filename": filename,
            "file_path": str(file_path)
        }

    @staticmethod
    def is_newer_version(new_ver: str, old_ver: str) -> bool:
        """
        Returns True if new_ver > old_ver.
        """
        def parse(v): return [int(x) for x in v.split(".")]
        return parse(new_ver) > parse(old_ver)