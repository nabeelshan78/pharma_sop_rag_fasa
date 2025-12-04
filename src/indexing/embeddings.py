import os
import logging
from typing import Optional

# --- LlamaIndex Imports ---
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core import Settings

# Use centralized logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# =================================================================================================


class EmbeddingManager:
    """
    Manages the Google Gemini Embedding Model.
    """
    
    @staticmethod
    def get_embedding_model(model_name: str = "models/text-embedding-004") -> GoogleGenAIEmbedding:
        """
        Instantiates the Google GenAI Embedding model.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.critical("GEMINI_API_KEY is missing! Embeddings cannot be generated.")
            raise ValueError("GEMINI_API_KEY is required in .env")
        try:
            # Initialize the model - text-embedding-004 outputs 768 dimensions.
            embed_model = GoogleGenAIEmbedding(
                model_name=model_name,
                api_key=api_key
            )
            return embed_model
        except Exception as e:
            logger.error(f"Failed to instantiate Gemini Embeddings: {e}")
            raise e

    @classmethod
    def configure_global_settings(cls):
        """
        Sets the Global LlamaIndex Settings. Call this ONCE at app startup.
        Anytime code calls VectorStoreIndex(nodes), it will use THIS model.
        """
        try:
            model = cls.get_embedding_model()
            Settings.embed_model = model
            logger.info(f">>>>>>>>>>>>>>>>>>>>>>>>>     Global Embeddings Configured: Google Gemini ({model.model_name})")
        except Exception as e:
            logger.critical("Failed to configure global embedding settings.")
            raise e



















# # --- SELF TEST ---
# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
    
#     print("--- Testing Embedding Connection ---")
#     try:
#         # 1. Configure
#         EmbeddingManager.configure_global_settings()
        
#         # 2. Test Generation
#         test_text = "Standard Operating Procedure for Quality Assurance."
#         embedding = Settings.embed_model.get_text_embedding(test_text)
        
#         print(f"✅ Success! Generated embedding vector.")
#         print(f"Dimensions: {len(embedding)} (Should be 768 for text-embedding-004)")
#         print(f"Sample: {embedding[:5]}...")
        
#     except Exception as e:
#         print(f"❌ Test Failed: {e}")