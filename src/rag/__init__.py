# src/rag/__init__.py

from src.rag.generator import LLMGenerator
from src.rag.retriever import FASAEngine

# 1. Initialize Global LLM Settings immediately on import.
# This ensures that whenever we use the RAG module, Gemini is ready.
LLMGenerator.configure_llm()

# 2. Export the Main Engine class for the UI to use
__all__ = ["FASAEngine"]

# --- SELF TEST ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("--- Running RAG Integration Test ---")
    try:
        # Initialize Engine
        engine = FASAEngine()
        
        # Test Query
        q = "What is the procedure for document retention?"
        result = engine.query(q)
        
        print(f"\n[Answer]:\n{result['answer']}")
        print(f"\n[Sources Found]: {len(result['sources'])}")
        if result['sources']:
            print(f"Top Source: {result['sources'][0]['sop_title']} (Page {result['sources'][0]['page']})")
            
    except Exception as e:
        print(f"Test Failed: {e}")