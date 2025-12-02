import os
import logging
from llama_index.llms.gemini import Gemini
from llama_index.core import Settings

# Use centralized logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class LLMGenerator:
    """
    Configures the Large Language Model (Brain).
    
    Standards:
    - Provider: Google Gemini
    - Model: gemini-1.5-flash (High speed, low cost, good reasoning)
    - Temperature: 0.0 (STRICT determinism for Pharma Compliance)
    """
    
    @staticmethod
    def configure_llm():
        """
        Sets the global LlamaIndex LLM settings.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.critical("❌ GEMINI_API_KEY is missing. RAG cannot function.")
            raise ValueError("GEMINI_API_KEY required in .env")

        try:
            # Temperature 0.0 is critical for "Zero Hallucination"
            llm = Gemini(
                model="models/gemini-2.0-flash-lite-001",
                api_key=api_key,
                temperature=0.5, 
                max_tokens=1024
            )
            
            # Apply Globally
            Settings.llm = llm
            logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>    Global LLM Configured: Gemini 2.0 Flash (Temp=0.5)")
            return llm
            
        except Exception as e:
            logger.error(f"LLM Setup failed: {e}")
            raise e