import os

# --- LlamaIndex Imports ---
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings


# =============================================================================
#  🔴 STEP 1: PASTE YOUR RUNPOD ADDRESS HERE
# =============================================================================
# Format: "http://IP_ADDRESS:PORT"
# Example: "http://213.173.110.198:54321" (Get this from the 'Connect' window)
RUNPOD_URL = "http://213.173.110.198:20332"
# Port: 11434 (TCP)

# =================================================================================================

class EmbeddingManager:
    """
    Manages the Local Ollama Embedding Model.
    """
    
    @staticmethod #ollama pull nomic-embed-text-v2-moe / nomic-embed-text
    def get_embedding_model(model_name: str = "nomic-embed-text-v2-moe") -> OllamaEmbedding:
        """
        Instantiates the Ollama Embedding model.
        Default is 'nomic-embed-text' (768 dimensions).
        """
        # base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        base_url = RUNPOD_URL
        
        try:
            print(f"Connecting to Ollama at {base_url} with model '{model_name}'...")
            embed_model = OllamaEmbedding(
                model_name=model_name,
                base_url=base_url,
                ollama_additional_kwargs={"mirostat": 0},
            )
            return embed_model
        except Exception as e:
            print(f"Failed to instantiate Ollama Embeddings: {e}")
            raise e

    @classmethod
    def configure_global_settings(cls):
        """
        Sets the Global LlamaIndex Settings. Call this ONCE at app startup.
        """
        try:
            model = cls.get_embedding_model()
            Settings.embed_model = model
            print(f">>>>>>>>>>>>>>>>>>>>>>>>>     Global Embeddings Configured: Ollama ({model.model_name})")
        except Exception as e:
            print("Failed to configure global embedding settings.")
            raise e




# --- SELF TEST ---
if __name__ == "__main__":
    print("--- Testing Ollama Connection ---")
    try:
        # 1. Configure
        EmbeddingManager.configure_global_settings()
        
        # 2. Test Generation
        test_text = "Standard Operating Procedure for Quality Assurance."
        embedding = Settings.embed_model.get_text_embedding(test_text)
        
        print(f"✅ Success! Generated embedding vector.")
        print(f"Dimensions: {len(embedding)} (Should be 768 for nomic-embed-text)")
        print(f"Sample: {embedding[:5]}...")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        print("Tip: Is Ollama running? Run 'ollama serve' in a separate terminal.")