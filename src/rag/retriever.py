import logging
from typing import Dict, Any, List

# LlamaIndex Core
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# Internal Modules
from src.indexing.vector_db import QdrantManager
from src.indexing.embeddings import EmbeddingManager
from src.rag.prompts import get_prompts

# Logger
try:
    from src.core.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class FASAEngine:
    """
    The RAG Controller.
    
    Flow:
    1. User Query -> Embedding
    2. Hybrid Search (Qdrant) -> Top 10 Nodes
    3. Reranking (SimilarityPostprocessor) -> Filter noise (Threshold 0.5)
    4. Synthesis (LLM) -> Answer with Citations
    """
    
    def __init__(self):
        logger.info("Initializing FASA RAG Engine...")
        
        # 1. Ensure Embeddings are Active (Gemini)
        EmbeddingManager.configure_global_settings()
        
        # 2. Connect to Database
        self.db_manager = QdrantManager()
        
        # 3. Load Index from Vector Store
        try:
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.db_manager.vector_store
            )
        except Exception as e:
            logger.critical(f"Failed to load Vector Index: {e}")
            raise e
            
        # 4. Build the Query Engine (The "Brain")
        self.query_engine = self._build_engine()

    def _build_engine(self) -> RetrieverQueryEngine:
        """
        Assembles the components: Retriever + Reranker + LLM Prompt.
        """
        # A. Retriever (Hybrid Search: Dense + Sparse)
        # alpha=0.5 gives equal weight to Keywords (BM25) and Semantics (Gemini)
        retriever = self.index.as_retriever(
            similarity_top_k=30, 
            vector_store_query_mode="hybrid", 
            alpha=0.5
        )
        
        # B. Post-Processor (The "Quality Filter")
        # If a chunk matches with less than 50% similarity, we drop it.
        # This prevents the LLM from hallucinating on irrelevant text.
        reranker = SimilarityPostprocessor(similarity_cutoff=0.50)
        
        # C. Response Synthesizer (The "Writer")
        # We inject our strict prompt here.
        synth = get_response_synthesizer(
            text_qa_template=get_prompts(),
            response_mode="compact"
        )
        
        # D. Assemble
        return RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=synth,
            node_postprocessors=[reranker]
        )

    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Public API for the UI.
        
        Returns:
            {
                "answer": str,
                "sources": List[Dict] (SOP Name, Version, Page, Score)
            }
        """
        if not query_text.strip():
            return {"answer": "Please enter a valid query.", "sources": []}
            
        logger.info(f"❓ Querying: '{query_text}'")
        
        try:
            # EXECUTE RAG
            response = self.query_engine.query(query_text)
            
            # PARSE SOURCES
            sources = []
            for node_w_score in response.source_nodes:
                # Critical: Extract keys that match ingestion/chunker.py
                meta = node_w_score.node.metadata
                
                source_info = {
                    "sop_title": meta.get("sop_title", "Unknown SOP"),
                    "version": meta.get("version_original", "N/A"),
                    "page": meta.get("page_label", "N/A"),
                    "file_name": meta.get("file_name", "N/A"),
                    "score": round(node_w_score.score, 3)
                }
                sources.append(source_info)

            logger.info(f">>>>>>>>>>>>>>>>>>>>>>     Generated Answer using {len(sources)} valid chunks.")
            
            return {
                "answer": str(response),
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Query Failed: {e}", exc_info=True)
            return {
                "answer": "System Error: Unable to process query. Please check logs.",
                "sources": []
            }