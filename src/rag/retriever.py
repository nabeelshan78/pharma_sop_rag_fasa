# src/rag/retriever.py
# Role: The engine that connects Vector DB + Prompts + LLM.
# Key Feature: It instantiates the VectorStoreManager you built in Step 2.

import logging
from typing import Dict, Any

from llama_index.core import VectorStoreIndex

# Internal Imports
from src.indexing.vector_db import QdrantManager
from src.rag.prompts import get_prompts
from src.rag.reranker import Reranker

# logger = logging.getLogger(__name__)
from src.core.logger import setup_logger
# This ensures consistent formatting across the whole app
logger = setup_logger(__name__)

class RAGRetriever:
    def __init__(self):
        # 1. Connect to Existing Vector DB
        self.db_manager = QdrantManager()
        
        # 2. Connect/Build the Index interface
        try:
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.db_manager.vector_store
            )
        except Exception as e:
            logger.error(f"Could not connect to Vector Index: {e}")
            raise e

        # 3. Build the Query Engine (The "Brain")
        self.query_engine = self._build_engine()

    def _build_engine(self):
        """
        Constructs the Hybrid Search Engine with Reranking.
        """
        prompts = get_prompts()
        postprocessors = Reranker.get_postprocessors(threshold=0.60)

        return self.index.as_query_engine(
            # Hybrid Search Settings
            vector_store_query_mode="hybrid", 
            alpha=0.5,  # Balance Keyword vs Semantic
            similarity_top_k=7,
            sparse_top_k=7,
            
            # Formatting & Safety
            text_qa_template=prompts,
            node_postprocessors=postprocessors,
            response_mode="compact"
        )

    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Public method to ask a question.
        Returns: { "answer": str, "sources": list }
        """
        if not query_text.strip():
            return {"answer": "Empty query.", "sources": []}

        response = self.query_engine.query(query_text)
        
        # Parse Response
        sources = []
        for node_w_score in response.source_nodes:
            meta = node_w_score.node.metadata
            sources.append({
                "sop_name": meta.get("sop_name", "Unknown"),
                "version": meta.get("version", "?"),
                "page": meta.get("page", "?"),
                "section": meta.get("section", "General"),
                "score": round(node_w_score.score, 3)
            })

        return {
            "answer": str(response),
            "sources": sources
        }