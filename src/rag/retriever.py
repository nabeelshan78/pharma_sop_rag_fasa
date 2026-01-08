from typing import Dict, Any, List, Optional
import re
import string

# LlamaIndex Core
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor import SimilarityPostprocessor
# It is now located in the 'types' submodule
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

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

        # --- NEW: Define Filter for "Active" status ---
        # This acts like a strict gatekeeper.
        active_filter = MetadataFilters(
            filters=[MetadataFilter(key="status", value="Active")]
        )

        # A. Retriever (Now includes the filter)
        retriever = self.index.as_retriever(
            similarity_top_k=7, 
            vector_store_query_mode="hybrid", 
            alpha=0.7,
            filters=active_filter  # <--- CRITICAL UPDATE HERE
        )

        # # A. Retriever
        # retriever = self.index.as_retriever(
        #     similarity_top_k=7, 
        #     vector_store_query_mode="hybrid", 
        #     alpha=0.7
        # )

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

        print(f">>> Performing Broad Multi-Keyword Search for: '{query_term}'")

        # Standard Punctuation from Python's library
        # Includes: !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
        PUNCTUATION_SET = set(string.punctuation)

        # Comprehensive list of English "Noise" words
        stop_words = {
            # To Be / Auxiliaries
            "is", "am", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "doing",
            "will", "would", "shall", "should", "can", "could", 
            "may", "might", "must", "ought",
            
            # Pronouns
            "i", "me", "my", "myself", "we", "us", "our", "ours", "ourselves",
            "you", "your", "yours", "yourself", "yourselves",
            "he", "him", "his", "himself", "she", "her", "hers", "herself",
            "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
            
            # Articles & Determiners
            "a", "an", "the", "this", "that", "these", "those",
            
            # Prepositions & Conjunctions
            "and", "but", "if", "or", "because", "as", "until", "while",
            "of", "at", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above", "below",
            "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
            "again", "further", "then", "once",
            
            # Common Adverbs & Others
            "here", "there", "when", "where", "why", "how",
            "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "just", "don", "now", "s", "t", "re", "ve", "m", "d", "ll"
        }

        ADDITIONAL_STOP_WORDS = {
        # --- 1. Expanded Prepositions & Location ---
        # Common in formal writing but usually noise for search
        "within", "without", "upon", "among", "amongst", "throughout", 
        "despite", "towards", "toward", "beside", "besides", "beyond", 
        "concerning", "regarding", "versus", "via", "per", "inside", 
        "outside", "near", "far", "amid", "amidst", "around",

        # --- 2. Logical Transitions & Connectors ---
        # SOPs use these to structure sentences ("Therefore, the user must...")
        "however", "therefore", "thus", "hence", "otherwise", "although", 
        "though", "whereas", "whenever", "wherever", "whereby", "wherein", 
        "whereupon", "unless", "except", "meanwhile", "furthermore", 
        "moreover", "nevertheless", "nonetheless", "instead", "eventually",

        # --- 3. Indefinite Pronouns & Quantifiers ---
        # These dilute the search for specific items
        "anyone", "anything", "anywhere", "anybody",
        "everyone", "everything", "everywhere", "everybody",
        "someone", "something", "somewhere", "somebody",
        "nobody", "nothing", "nowhere", "none",
        "either", "neither", "another", "plenty", "various", "amount",
        "whole", "half", "certain", "entire", "various", "several",

        # --- 4. Extremely Generic Verbs (All Tenses) ---
        # These actions are too vague to be useful keywords
        "use", "used", "using", "uses",       # "Using a beaker" -> Search "Beaker"
        "make", "made", "making", "makes",    # "Make a solution" -> Search "Solution"
        "keep", "kept", "keeping", "keeps", 
        "let", "lets", "letting", 
        "put", "putting", "puts",
        "take", "took", "taken", "taking", "takes",
        "get", "got", "getting", "gets", "gotten",
        "go", "went", "gone", "going", "goes",
        "come", "came", "coming", "comes",
        "become", "became", "becoming", "becomes",
        "seem", "seemed", "seeming", "seems",
        "look", "looked", "looking", "looks",
        "find", "found", "finding", "finds",
        "try", "tried", "trying", "tries",
        "need", "needed", "needing", "needs",
        "want", "wanted", "wanting", "wants",
        "say", "said", "saying", "says",
        "know", "knew", "known", "knowing", "knows",
        "think", "thought", "thinking", "thinks", "what",

        # --- 5. Common SOP/Document "Filler" ---
        # Words that appear in almost every document but aren't the *topic*
        "etc", "ie", "eg", "viz", "ex", "example", 
        "please", "kindly", "follow", "followed", "following", # "Following procedure" -> "Procedure"
        "ensure", "ensuring", "ensured",  # Very common in SOPs ("Ensure safety")
        "describe", "described", "describing", 
        "refer", "referred", "referring", "reference",
        "related", "relating", "relate",
        "accordance", "according",  # "In accordance with"
        "stated", "stating", "states",
        "listed", "listing", "lists",
        "include", "included", "including", "includes",
        "contain", "contained", "containing", "contains",
        "consist", "consisted", "consisting", "consists",
        "base", "based", "basing", "bases",
        "high", "low", "good", "bad", "big", "small", "main", "major", "minor",
        
        # --- 6. Time Fillers ---
        "always", "never", "often", "sometimes", "usually", "rarely",
        "daily", "weekly", "monthly", "yearly", "annually",
        "today", "yesterday", "tomorrow", "now", "then", "later", 
        "early", "soon", "already", "recently", "currently"
        }
        stop_words.update(ADDITIONAL_STOP_WORDS)
        
        # --- 2. CLEAN THE QUERY ---
        # A. Lowercase
        cleaned_query = query_term.lower()
            
        # B. Remove Punctuation (replace with space)
        # e.g. "glove,safety" -> "glove safety"
        for char in string.punctuation:
            cleaned_query = cleaned_query.replace(char, " ")
                
        # C. Split and Filter Stop Words
        raw_terms = cleaned_query.split()

        # Keep term ONLY if it is NOT in stop_words
        filtered_terms = [t for t in raw_terms if t not in stop_words]
        
        # # Fallback: If user typed ONLY stop words (e.g., "The and"), keep original to avoid empty search
        if not filtered_terms:
            # filtered_terms = raw_terms
            return []

        print(f">>> Cleaned Search Terms: {filtered_terms}")

        try:
            # Escape them to handle special chars like '+', '?' safely
            safe_terms = [re.escape(t) for t in filtered_terms]
            
            # Pattern to find ANY of the words (Used for both filtering and highlighting)
            # regex structure: \b(word1|word2|word3)\b (OR Logic)
            highlight_pattern = re.compile(rf"\b({'|'.join(safe_terms)})\b", re.IGNORECASE)

            # 2. RETRIEVE CANDIDATES (Sparse/BM25)
            # We use BM25 to get candidates that contain these words
            active_filter = MetadataFilters(
                filters=[MetadataFilter(key="status", value="Active")]
            )

            broad_retriever = self.index.as_retriever(
                similarity_top_k=100,
                vector_store_query_mode="sparse", 
                alpha=0.0,
                filters=active_filter 
            )

            cleaned_query_str = " ".join(safe_terms)
            
            candidate_nodes = broad_retriever.retrieve(cleaned_query_str)
            
            sop_grouping = {}

            # 3. FILTER & PROCESS
            for node_w_score in candidate_nodes:
                node = node_w_score.node
                meta = node.metadata
                
                text_to_scan = meta.get("original_text", node.text)
                
                # --- FLEXIBLE "OR" LOGIC ---
                # We simply check if the regex finds AT LEAST ONE of the words.
                if not highlight_pattern.search(text_to_scan):
                    continue  # Skip only if NONE of the words are found

                # --- IF MATCH FOUND ---
                sop_title = meta.get("sop_title", "Unknown SOP")
                file_name = meta.get("file_name", "Unknown File")
                page_label = meta.get("page_label", "?")

                if sop_title not in sop_grouping:
                    sop_grouping[sop_title] = {
                        "file_name": file_name,
                        "highest_score": node_w_score.score, 
                        "match_count": 0,
                        "snippets": []
                    }
                
                group = sop_grouping[sop_title]
                group["match_count"] += 1
                
                # Clean text for snippet presentation
                clean_text = text_to_scan
                if "Source:" in clean_text:
                    parts = clean_text.split("\n", 1)
                    if len(parts) > 1: clean_text = parts[1]

                # Generate Snippets (Show context around found keywords)
                if len(group["snippets"]) < 3:
                    # Find occurrences of ANY keyword to create the snippet
                    iterator = highlight_pattern.finditer(clean_text)
                    for m in iterator:
                        start = max(0, m.start() - 60)
                        end = min(len(clean_text), m.end() + 60)
                        snippet = clean_text[start:end].replace("\n", " ")
                        
                        group["snippets"].append(f"• (Pg {page_label}) ...{snippet}...")
                        
                        # Stop after 3 snippets to avoid clutter
                        if len(group["snippets"]) >= 3: break

            # 4. FORMAT OUTPUT
            results = []
            for title, data in sop_grouping.items():
                results.append({
                    "SOP Title": title,
                    "File Name": data["file_name"],
                    "Relevance": round(data["highest_score"], 3),
                    "Matches Found": data["match_count"],
                    "Snippets": "\n".join(data["snippets"])
                })
            
            # Sort by relevance score (provided by BM25)
            results.sort(key=lambda x: x["Relevance"], reverse=True)
            print(f">>> Broad Search Complete. Found matches in {len(results)} SOPs.")
            return results

        except Exception as e:
            print(f"Search Failed: {e}")
            return []



    # def search(self, query_term: str) -> List[Dict[str, Any]]:
    #     if not query_term.strip():
    #         return []

    #     print(f">>> Performing Robust Regex Search for: '{query_term}'")
        
    #     try:
    #         safe_term = re.escape(query_term.strip())
    #         pattern = re.compile(rf"\b{safe_term}\b", re.IGNORECASE) 

    #         # 1. Define Filter
    #         active_filter = MetadataFilters(
    #             filters=[MetadataFilter(key="status", value="Active")]
    #         )

    #         # 2. Pass it to the retriever
    #         broad_retriever = self.index.as_retriever(
    #             similarity_top_k=100,
    #             vector_store_query_mode="sparse", 
    #             alpha=0.0,
    #             filters=active_filter # <--- Add this line
    #         )

    #         # broad_retriever = self.index.as_retriever(
    #         #     similarity_top_k=100,
    #         #     vector_store_query_mode="sparse", # Use BM25
    #         #     alpha=0.0
    #         # )
    #         candidate_nodes = broad_retriever.retrieve(query_term)
            
    #         sop_grouping = {}

    #         for node_w_score in candidate_nodes:
    #             node = node_w_score.node
    #             meta = node.metadata
                
    #             text_to_scan = meta.get("original_text", node.text)
                
    #             if pattern.search(text_to_scan):
                    
    #                 sop_title = meta.get("sop_title", "Unknown SOP")
    #                 file_name = meta.get("file_name", "Unknown File")
    #                 page_label = meta.get("page_label", "?")

    #                 # Initialize Group if needed
    #                 if sop_title not in sop_grouping:
    #                     sop_grouping[sop_title] = {
    #                         "file_name": file_name,
    #                         "highest_score": node_w_score.score, 
    #                         "match_count": 0,
    #                         "snippets": []
    #                     }
                    
    #                 # Update Stats
    #                 group = sop_grouping[sop_title]
    #                 group["match_count"] += 1
                    
    #                 clean_text = text_to_scan
    #                 if "Source:" in clean_text:
    #                     parts = clean_text.split("\n", 1)
    #                     if len(parts) > 1: clean_text = parts[1]

    #                 if len(group["snippets"]) < 3:
    #                     iterator = pattern.finditer(clean_text)
    #                     for m in iterator:
    #                         start = max(0, m.start() - 60)
    #                         end = min(len(clean_text), m.end() + 60)
    #                         snippet = clean_text[start:end].replace("\n", " ")
    #                         group["snippets"].append(f"• (Pg {page_label}) ...{snippet}...")
                            
    #                         if len(group["snippets"]) >= 3: break

    #         # Format Output
    #         results = []
    #         for title, data in sop_grouping.items():
    #             results.append({
    #                 "SOP Title": title,
    #                 "File Name": data["file_name"],
    #                 "Relevance": round(data["highest_score"], 3),
    #                 "Matches Found": data["match_count"],
    #                 "Snippets": "\n".join(data["snippets"])
    #             })
            
    #         results.sort(key=lambda x: x["Relevance"], reverse=True)
    #         print(f">>> Regex Search Complete. Found term in {len(results)} SOPs.")
    #         return results

    #     except Exception as e:
    #         print(f"Regex Search Failed: {e}")
    #         return []



    
# New AND
    # def search(self, query_term: str) -> List[Dict[str, Any]]:
    #     if not query_term.strip():
    #         return []

    #     print(f">>> Performing Robust Multi-Keyword Search for: '{query_term}'")
        
    #     try:
    #         # 1. PREPARE TERMS
    #         # Split query into individual words for "AND" logic
    #         # e.g., "safety gloves" -> ["safety", "gloves"]
    #         raw_terms = query_term.strip().split()
    #         # Escape them to handle special chars like '+', '?' safely
    #         safe_terms = [re.escape(t) for t in raw_terms]
            
    #         # Pattern to find ANY of the words (for snippet highlighting)
    #         # regex structure: \b(word1|word2|word3)\b
    #         highlight_pattern = re.compile(rf"\b({'|'.join(safe_terms)})\b", re.IGNORECASE)

    #         # 2. RETRIEVE CANDIDATES (Sparse/BM25)
    #         # We use BM25 to get the top 100 candidates that likely contain these words
    #         active_filter = MetadataFilters(
    #             filters=[MetadataFilter(key="status", value="Active")]
    #         )

    #         broad_retriever = self.index.as_retriever(
    #             similarity_top_k=100,
    #             vector_store_query_mode="sparse", 
    #             alpha=0.0,
    #             filters=active_filter 
    #         )
            
    #         candidate_nodes = broad_retriever.retrieve(query_term)
            
    #         sop_grouping = {}

    #         # 3. FILTER & PROCESS
    #         for node_w_score in candidate_nodes:
    #             node = node_w_score.node
    #             meta = node.metadata
                
    #             text_to_scan = meta.get("original_text", node.text)
                
    #             # --- THE "AND" LOGIC (Strictness) ---
    #             # Check if ALL terms are present in this chunk.
    #             # If the user types 5 words, we ensure all 5 exist here.
    #             all_terms_present = True
    #             for term in safe_terms:
    #                 # Search for 'term' as a whole word (\b) case-insensitively
    #                 if not re.search(rf"\b{term}\b", text_to_scan, re.IGNORECASE):
    #                     all_terms_present = False
    #                     break
                
    #             # If even one word is missing, skip this chunk
    #             if not all_terms_present:
    #                 continue

    #             # --- IF MATCH FOUND ---
    #             sop_title = meta.get("sop_title", "Unknown SOP")
    #             file_name = meta.get("file_name", "Unknown File")
    #             page_label = meta.get("page_label", "?")

    #             if sop_title not in sop_grouping:
    #                 sop_grouping[sop_title] = {
    #                     "file_name": file_name,
    #                     "highest_score": node_w_score.score, 
    #                     "match_count": 0,
    #                     "snippets": []
    #                 }
                
    #             group = sop_grouping[sop_title]
    #             group["match_count"] += 1
                
    #             # Clean text for snippet presentation
    #             clean_text = text_to_scan
    #             if "Source:" in clean_text:
    #                 parts = clean_text.split("\n", 1)
    #                 if len(parts) > 1: clean_text = parts[1]

    #             # Generate Snippets (Show context around found keywords)
    #             if len(group["snippets"]) < 3:
    #                 # Find occurrences of ANY keyword to create the snippet
    #                 iterator = highlight_pattern.finditer(clean_text)
    #                 for m in iterator:
    #                     start = max(0, m.start() - 60)
    #                     end = min(len(clean_text), m.end() + 60)
    #                     snippet = clean_text[start:end].replace("\n", " ")
                        
    #                     group["snippets"].append(f"• (Pg {page_label}) ...{snippet}...")
                        
    #                     # Stop after 3 snippets to avoid clutter
    #                     if len(group["snippets"]) >= 3: break

    #         # 4. FORMAT OUTPUT
    #         results = []
    #         for title, data in sop_grouping.items():
    #             results.append({
    #                 "SOP Title": title,
    #                 "File Name": data["file_name"],
    #                 "Relevance": round(data["highest_score"], 3),
    #                 "Matches Found": data["match_count"],
    #                 "Snippets": "\n".join(data["snippets"])
    #             })
            
    #         # Sort by relevance score (provided by BM25)
    #         results.sort(key=lambda x: x["Relevance"], reverse=True)
    #         print(f">>> Multi-Keyword Search Complete. Found matches in {len(results)} SOPs.")
    #         return results

    #     except Exception as e:
    #         print(f"Search Failed: {e}")
    #         return []
        


# OR
def search(self, query_term: str) -> List[Dict[str, Any]]:
        if not query_term.strip():
            return []

        print(f">>> Performing Broad Multi-Keyword Search for: '{query_term}'")
        
        try:
            # 1. PREPARE TERMS
            # Split query into individual words
            # e.g., "safety gloves" -> ["safety", "gloves"]
            raw_terms = query_term.strip().split()
            # Escape them to handle special chars like '+', '?' safely
            safe_terms = [re.escape(t) for t in raw_terms]
            
            # Pattern to find ANY of the words (Used for both filtering and highlighting)
            # regex structure: \b(word1|word2|word3)\b (OR Logic)
            highlight_pattern = re.compile(rf"\b({'|'.join(safe_terms)})\b", re.IGNORECASE)

            # 2. RETRIEVE CANDIDATES (Sparse/BM25)
            # We use BM25 to get candidates that contain these words
            active_filter = MetadataFilters(
                filters=[MetadataFilter(key="status", value="Active")]
            )

            broad_retriever = self.index.as_retriever(
                similarity_top_k=100,
                vector_store_query_mode="sparse", 
                alpha=0.0,
                filters=active_filter 
            )
            
            candidate_nodes = broad_retriever.retrieve(query_term)
            
            sop_grouping = {}

            # 3. FILTER & PROCESS
            for node_w_score in candidate_nodes:
                node = node_w_score.node
                meta = node.metadata
                
                text_to_scan = meta.get("original_text", node.text)
                
                # --- FLEXIBLE "OR" LOGIC ---
                # We simply check if the regex finds AT LEAST ONE of the words.
                if not highlight_pattern.search(text_to_scan):
                    continue  # Skip only if NONE of the words are found

                # --- IF MATCH FOUND ---
                sop_title = meta.get("sop_title", "Unknown SOP")
                file_name = meta.get("file_name", "Unknown File")
                page_label = meta.get("page_label", "?")

                if sop_title not in sop_grouping:
                    sop_grouping[sop_title] = {
                        "file_name": file_name,
                        "highest_score": node_w_score.score, 
                        "match_count": 0,
                        "snippets": []
                    }
                
                group = sop_grouping[sop_title]
                group["match_count"] += 1
                
                # Clean text for snippet presentation
                clean_text = text_to_scan
                if "Source:" in clean_text:
                    parts = clean_text.split("\n", 1)
                    if len(parts) > 1: clean_text = parts[1]

                # Generate Snippets (Show context around found keywords)
                if len(group["snippets"]) < 3:
                    # Find occurrences of ANY keyword to create the snippet
                    iterator = highlight_pattern.finditer(clean_text)
                    for m in iterator:
                        start = max(0, m.start() - 60)
                        end = min(len(clean_text), m.end() + 60)
                        snippet = clean_text[start:end].replace("\n", " ")
                        
                        group["snippets"].append(f"• (Pg {page_label}) ...{snippet}...")
                        
                        # Stop after 3 snippets to avoid clutter
                        if len(group["snippets"]) >= 3: break

            # 4. FORMAT OUTPUT
            results = []
            for title, data in sop_grouping.items():
                results.append({
                    "SOP Title": title,
                    "File Name": data["file_name"],
                    "Relevance": round(data["highest_score"], 3),
                    "Matches Found": data["match_count"],
                    "Snippets": "\n".join(data["snippets"])
                })
            
            # Sort by relevance score (provided by BM25)
            results.sort(key=lambda x: x["Relevance"], reverse=True)
            print(f">>> Broad Search Complete. Found matches in {len(results)} SOPs.")
            return results

        except Exception as e:
            print(f"Search Failed: {e}")
            return []