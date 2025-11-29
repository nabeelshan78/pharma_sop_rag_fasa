# indexing/embeddings.py
# Role: Single source of truth for embedding models.
# Enhancement: Encapsulated in a factory class with error handling to ensure API keys exist before crashing deep in the pipeline.

import os
import logging
from typing import Optional

# --- LlamaIndex Imports ---
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core import Settings

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """
    Manages the Google Gemini Embedding Model configuration.
    """
    
    @staticmethod
    def get_embedding_model(model_name: str = "models/text-embedding-004") -> GoogleGenAIEmbedding:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.critical("GEMINI_API_KEY is missing from environment variables.")
            raise ValueError("GEMINI_API_KEY is required.")

        try:
            embed_model = GoogleGenAIEmbedding(
                model_name=model_name,
                api_key=api_key
            )
            # Set global settings for LlamaIndex
            Settings.embed_model = embed_model
            logger.info(f"Google Gemini Embeddings initialized: {model_name}")
            return embed_model
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Embeddings: {e}")
            raise e