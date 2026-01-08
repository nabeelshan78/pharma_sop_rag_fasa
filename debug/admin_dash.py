import sys
import os
from pathlib import Path

# 1. Get the path to the project root (one level up from 'debug')
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent

# 2. Add the project root to Python's system path
sys.path.append(str(project_root))

# --- NOW you can safely import from src ---
import pandas as pd
from dotenv import load_dotenv
from qdrant_client.http import models as rest_models
from src.rag import FASAEngine  # <--- This line will now work




def get_all_sops():
    """
    Retrieves metadata DIRECTLY from Qdrant (Source of Truth).
    """
    engine = FASAEngine()
    
    # 2. Access the Qdrant Client directly
    try:
        # Navigate through LlamaIndex to get the native Qdrant client
        # structure: index -> vector_store -> client
        client = engine.index.vector_store.client
        collection_name = "fasa_sops"  # Ensure this matches your ingest config
        
        # 3. Fetch data (Scroll)
        # We fetch up to 10,000 points to ensure we get everything.
        # with_payload=True is crucial to get the metadata.
        response = client.scroll(
            collection_name=collection_name,
            limit=10000, 
            with_payload=True,
            with_vectors=False # We don't need the vectors, just metadata
        )
        points = response[0] # scroll returns (points, offset)
        
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")
        return pd.DataFrame()

    # 4. Process & Deduplicate
    unique_sops = {}

    for point in points:
        meta = point.payload
        if not meta:
            continue
            
        file_name = meta.get("file_name")

        # Deduplication Logic
        if file_name and file_name not in unique_sops:
            status_str = meta.get("status", "Active")
            is_active = True if status_str == "Active" else False

            unique_sops[file_name] = {
                "File Name": file_name,
                "Title": meta.get("sop_title", "Unknown Title"),
                "Doc Number": meta.get("document_number", "---"),
                "Version": meta.get("version_number", "---"),
                "Status": status_str,
                "Active": is_active
            }

    # 5. Return DataFrame
    if not unique_sops:
        return pd.DataFrame(columns=["File Name", "Title", "Doc Number", "Version", "Status", "Active"])
        
    return pd.DataFrame(list(unique_sops.values()))


print(get_all_sops())