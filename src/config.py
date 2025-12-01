import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env variables immediately upon import
load_dotenv()

# Setup simple logger for config errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CONFIG")

class Settings:
    """
    Central Configuration Registry.
    Acts as the Single Source of Truth for Paths, Keys, and Constants.
    """
    
    # --- Project Paths ---
    # Robust root detection (Works even if called from subfolders)
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Data Directories
    DATA_DIR = BASE_DIR / "data"
    RAW_SOPS_DIR = DATA_DIR / "raw_sops"
    VECTOR_STORE_DIR = DATA_DIR / "vector_store"
    TEMP_DIR = DATA_DIR / "temp_uploads"

    # --- API Keys (Secrets) ---
    # We use getenv with default None to allow validation logic to catch missing keys later
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
    
    # CRITICAL: Missing in your original code
    LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY", None) 
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)

    # --- Qdrant Settings ---
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "fasa_sops_llama")
    
    # --- Model Configuration ---
    # We stick to 1.5-flash for Production stability (2.0-flash-lite is experimental)
    LLM_MODEL = "models/gemini-1.5-flash"
    # Standard Gemini embedding model (768 dimensions)
    EMBED_MODEL = "models/text-embedding-004"
    
    # --- RAG Parameters ---
    # 0.5 = Balanced Hybrid (50% Keyword / 50% Vector)
    HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.5"))
    
    # Text Splitting (Optimized for SOPs)
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 200

    def validate(self):
        """
        Self-Diagnostic: Ensures all critical keys are present.
        Call this at the start of main.py or bulk_ingest.py
        """
        missing = []
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not self.LLAMA_CLOUD_API_KEY:
            missing.append("LLAMA_CLOUD_API_KEY")
        
        if missing:
            error_msg = f"❌ CRITICAL CONFIG ERROR: Missing Environment Variables: {', '.join(missing)}"
            logger.critical(error_msg)
            raise ValueError(error_msg)
            
        # Ensure directories exist
        self.DATA_DIR.mkdir(exist_ok=True)
        self.RAW_SOPS_DIR.mkdir(exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)

# Singleton instance
settings = Settings()

# Auto-validate on import to fail fast? 
# Usually better to call explicitly, but for safety in this project:
# settings.validate()