# src/rag/__init__.py
# Role: Initializes the LLM settings when the module is imported.

from .generator import LLMGenerator
from .retriever import RAGRetriever

# Initialize Global Settings immediately
LLMGenerator.setup_llm()