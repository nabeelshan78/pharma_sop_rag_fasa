# src/rag/generator.py
# Role: Configures the LLM (Gemini).
# Key Feature: temperature=0.0. In Creative writing, we want 0.7. In Pharma/Law, you want 0.0 to ensure consistency.

import os
import logging
from llama_index.llms.gemini import Gemini
from llama_index.core import Settings

logger = logging.getLogger(__name__)

class LLMGenerator:
    @staticmethod
    def setup_llm():
        """
        Configures the Gemini LLM with strict parameters.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing.")

        try:
            # Using flash-lite for speed, or pro for reasoning.
            # Temperature 0.0 is non-negotiable for SOPs.
            llm = Gemini(
                model="models/gemini-2.0-flash-lite-001",
                api_key=api_key,
                temperature=0.0, 
                max_tokens=1024
            )
            Settings.llm = llm
            logger.info("LLM initialized: Gemini 2.0 Flash Lite (Temp=0.0)")
            return llm
        except Exception as e:
            logger.error(f"LLM Setup failed: {e}")
            raise e