# src/rag/reranker.py
# Role: Quality Control.
# Key Feature: Similarity Cutoff. If the vector search finds chunks, but they are only 40% relevant, this module discards them to prevent the LLM from trying to "make sense" of irrelevant text.

from llama_index.core.postprocessor import SimilarityPostprocessor

class Reranker:
    @staticmethod
    def get_postprocessors(threshold: float = 0.65):
        """
        Returns a list of post-processors.
        
        Args:
            threshold (float): 0.0 to 1.0. 
            0.65 is a safe bet for cosine similarity. 
            Anything below this is likely noise.
        """
        # Checks the similarity score of retrieved nodes.
        # If score < threshold, the node is dropped.
        cutoff = SimilarityPostprocessor(similarity_cutoff=threshold)
        
        return [cutoff]