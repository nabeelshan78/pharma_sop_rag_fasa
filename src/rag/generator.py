import os
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings


RUNPOD_URL = "http://213.173.110.198:20332"

class LLMGenerator:
    """
    Configures the Large Language Model (Brain) using Local Ollama
    """
    
    @staticmethod
    def configure_llm():
        # base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # model_name = "llama3.2:7b" # "llama3.2:3b" "qwen2.5:1.5b" "llama3:8b"
        # model_name = "llama3.2:3b" # Use this --> llama3.1:8b 

        base_url = RUNPOD_URL
        model_name = "llama3.1:8b"

        try:
            print(f"Connecting to Ollama LLM at {base_url}...")
            
            llm = Ollama(
                model=model_name,
                base_url=base_url,
                temperature=0.3,
                request_timeout=3000.0,
                context_window=4096, # Use this ---> 8192
                additional_kwargs={
                "num_ctx": 4096 # Use this ---> 8192
            }
            )
            
            Settings.llm = llm
            print(f">>>>>>>>>>>>>>>>>>>>>>>>>     Global LLM Configured: Ollama ({model_name})")
            return llm
            
        except Exception as e:
            print(f"LLM Setup failed: {e}")
            raise e