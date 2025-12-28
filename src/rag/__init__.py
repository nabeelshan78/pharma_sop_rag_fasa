# src/rag/__init__.py

from src.rag.generator import LLMGenerator
from src.rag.retriever import FASAEngine

# 1. Initialize Global LLM Settings immediately on import.
LLMGenerator.configure_llm()

# 2. Export the Main Engine class for the UI to use
__all__ = ["FASAEngine"]