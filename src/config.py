import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env variables immediately upon import
load_dotenv()

class Settings:
    # --- Project Paths ---
    # Automatically finds the root directory relative to this file
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    TEMP_DIR = BASE_DIR / "temp_sops"

    # --- Qdrant Configuration ---
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "fasa_sops_llama")

    # --- Google Gemini Configuration ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Using Flash Lite for speed/cost in demo, can swap to Pro for reasoning
    LLM_MODEL = "models/gemini-2.0-flash-lite-001"
    EMBED_MODEL = "models/text-embedding-004"
    
    # --- RAG Parameters ---
    # 0.5 = Balanced Hybrid (50% Keyword / 50% Vector)
    HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.5"))
    
    # Text Splitting Settings (Optimized for SOP sections)
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 200

# Singleton instance to import elsewhere
settings = Settings()