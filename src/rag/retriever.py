from typing import Dict, Any, List, Optional
import re

# LlamaIndex Core
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor import SimilarityPostprocessor
# It is now located in the 'types' submodule
from llama_index.core.postprocessor.types import BaseNodePostprocessor

# Internal Modules
from src.indexing.vector_db import QdrantManager
from src.indexing.embeddings import EmbeddingManager
from src.rag.prompts import get_prompts

# --- HELPER CLASS FOR TEXT SWAPPING ---
class MetadataTextRestorer(BaseNodePostprocessor):
    """
    A custom Postprocessor that runs immediately after retrieval.
    """
    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        
        for node_w_score in nodes:
            node = node_w_score.node
            if "original_text" in node.metadata:
                node.text = node.metadata["original_text"]
        return nodes

# --- MAIN ENGINE CLASS ---
class FASAEngine:
    """
    The RAG Controller (Ollama).
    """
    
    def __init__(self):
        print("Initializing FASA RAG Engine...")
        
        # 1. Ensure Embeddings are Active
        EmbeddingManager.configure_global_settings()
        
        # 2. Connect to Database
        self.db_manager = QdrantManager()
        
        # 3. Load Index from Vector Store
        try:
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.db_manager.vector_store
            )
        except Exception as e:
            print(f"Failed to load Vector Index: {e}")
            raise e
            
        # 4. Build the Query Engine (The "Brain")
        self.query_engine = self._build_engine()

    def _build_engine(self) -> RetrieverQueryEngine:
        # A. Retriever
        retriever = self.index.as_retriever(
            similarity_top_k=7, 
            vector_store_query_mode="hybrid", 
            alpha=0.7
        )

        # --- NEW: SCORE FILTER ---
        # This drops any chunk with a score below 0.05
        cutoff_processor = SimilarityPostprocessor(cutoff=0.05)

        # B. Postprocessor (The "Fixer")
        text_restorer = MetadataTextRestorer()

        # C. Response Synthesizer (The "Writer")
        synth = get_response_synthesizer(
            text_qa_template=get_prompts(),
            response_mode="compact"
        )
        
        # D. Assemble
        return RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=synth,
            node_postprocessors=[cutoff_processor, text_restorer]
        )

    def query(self, query_text: str) -> Dict[str, Any]:
        if not query_text.strip():
            return {"answer": "Please enter a valid query.", "sources": []}
            
        print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   Querying: '{query_text}'")
        
        try:
            normalized_query = query_text.lower()

            # EXECUTE RAG
            response = self.query_engine.query(normalized_query)
            
            # PARSE SOURCES
            sources = []
            for node_w_score in response.source_nodes:
                meta = node_w_score.node.metadata
                
                # Extract metadata
                source_info = {
                    "sop_title": meta.get("sop_title", "Unknown SOP"),
                    "file_name": meta.get("file_name", "N/A"),
                    "page": meta.get("page_label", "N/A"),
                    "score": round(node_w_score.score, 3)
                }
                sources.append(source_info)

            print(f">>>>>>>>>>>>>>>>>>>>>>     Generated Answer using {len(sources)} valid chunks.")
            
            return {
                "answer": str(response),
                "sources": sources
            }

        except Exception as e:
            print(f"Query Failed: {e}")
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()
            return {
                "answer": "System Error: Unable to process query. Please ensure Ollama is running.",
                "sources": []
            }
        

    def search(self, query_term: str) -> List[Dict[str, Any]]:
        if not query_term.strip():
            return []

        print(f">>> Performing Robust Regex Search for: '{query_term}'")
        
        try:
            safe_term = re.escape(query_term.strip())
            pattern = re.compile(rf"\b{safe_term}\b", re.IGNORECASE) 

            broad_retriever = self.index.as_retriever(
                similarity_top_k=100,
                vector_store_query_mode="sparse", # Use BM25
                alpha=0.0
            )
            candidate_nodes = broad_retriever.retrieve(query_term)
            
            sop_grouping = {}

            for node_w_score in candidate_nodes:
                node = node_w_score.node
                meta = node.metadata
                
                text_to_scan = meta.get("original_text", node.text)
                
                if pattern.search(text_to_scan):
                    
                    sop_title = meta.get("sop_title", "Unknown SOP")
                    file_name = meta.get("file_name", "Unknown File")
                    page_label = meta.get("page_label", "?")

                    # Initialize Group if needed
                    if sop_title not in sop_grouping:
                        sop_grouping[sop_title] = {
                            "file_name": file_name,
                            "highest_score": node_w_score.score, 
                            "match_count": 0,
                            "snippets": []
                        }
                    
                    # Update Stats
                    group = sop_grouping[sop_title]
                    group["match_count"] += 1
                    
                    clean_text = text_to_scan
                    if "Source:" in clean_text:
                        parts = clean_text.split("\n", 1)
                        if len(parts) > 1: clean_text = parts[1]

                    if len(group["snippets"]) < 3:
                        iterator = pattern.finditer(clean_text)
                        for m in iterator:
                            start = max(0, m.start() - 60)
                            end = min(len(clean_text), m.end() + 60)
                            snippet = clean_text[start:end].replace("\n", " ")
                            group["snippets"].append(f"• (Pg {page_label}) ...{snippet}...")
                            
                            if len(group["snippets"]) >= 3: break

            # Format Output
            results = []
            for title, data in sop_grouping.items():
                results.append({
                    "SOP Title": title,
                    "File Name": data["file_name"],
                    "Relevance": round(data["highest_score"], 3),
                    "Matches Found": data["match_count"],
                    "Snippets": "\n".join(data["snippets"])
                })
            
            results.sort(key=lambda x: x["Relevance"], reverse=True)
            print(f">>> Regex Search Complete. Found term in {len(results)} SOPs.")
            return results

        except Exception as e:
            print(f"Regex Search Failed: {e}")
            return []