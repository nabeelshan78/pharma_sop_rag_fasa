# app.py
# Role: The Frontend.
# Key Feature: No requests library. It imports src modules directly.

import streamlit as st
import pandas as pd
import time
import os
from dotenv import load_dotenv

# --- Load Environment ---
load_dotenv()

# --- Internal Imports ---
# We talk directly to the Python logic, no API middleware for this demo
from src.ingestion import IngestionPipeline
from src.rag import RAGRetriever

# --- Page Config ---
st.set_page_config(page_title="FASA Pharma Demo", page_icon="💊", layout="wide")

# --- Session State ---
if "rag_engine" not in st.session_state:
    # Initialize the RAG engine once (Cache resource)
    with st.spinner("Initializing AI Brain..."):
        try:
            st.session_state.rag_engine = RAGRetriever()
            st.session_state.ingest_pipeline = IngestionPipeline()
            st.success("System Ready.")
        except Exception as e:
            st.error(f"System Failed to Init: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper: Display Citations ---
def format_citations(sources):
    if not sources: return None
    df = pd.DataFrame(sources)
    # Deduplicate for clean display
    df = df.drop_duplicates(subset=["sop_name", "page"])
    return df

# # --- UI: Sidebar ---
# with st.sidebar:
#     st.title("💊 FASA Control")
#     st.markdown("---")
    
#     # File Uploader
#     uploaded_files = st.file_uploader("Upload SOPs (PDF)", accept_multiple_files=True)
    
#     if uploaded_files and st.button("Ingest Documents"):
#         if "ingest_pipeline" in st.session_state:
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             # Create a temp dir to save files for processing
#             os.makedirs("temp_sops", exist_ok=True)
            
#             for i, file in enumerate(uploaded_files):
#                 status_text.text(f"Processing {file.name}...")
#                 temp_path = os.path.join("temp_sops", file.name)
                
#                 with open(temp_path, "wb") as f:
#                     f.write(file.getbuffer())
                
#                 # Run Pipeline
#                 try:
#                     nodes = st.session_state.ingest_pipeline.process_file(temp_path)
#                     # Index Immediately
#                     # We need to access the DB manager inside the RAG engine to insert
#                     st.session_state.rag_engine.db_manager.insert_nodes(nodes)
#                 except Exception as e:
#                     st.error(f"Error on {file.name}: {e}")
                
#                 # Cleanup
#                 os.remove(temp_path)
#                 progress_bar.progress((i + 1) / len(uploaded_files))
            
#             st.success("Ingestion Complete!")
#             time.sleep(1)
#             st.rerun()

#     if st.button("Clear Chat"):
#         st.session_state.messages = []
#         st.rerun()

# --- UI: Chat ---
st.title("FASA: Pharma Regulatory Assistant")
st.caption("Zero-Hallucination Mode Enabled | Hybrid Search Active")

# Render History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("View Verified Sources"):
                st.dataframe(format_citations(msg["sources"]), width="stretch")

# Input
if prompt := st.chat_input("Ask about an SOP..."):
    # User Msg
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI Msg
    with st.chat_message("assistant"):
        with st.spinner("Consulting SOPs..."):
            try:
                # Direct Call to Logic
                response_data = st.session_state.rag_engine.query(prompt)
                
                answer = response_data["answer"]
                sources = response_data["sources"]
                
                st.markdown(answer)
                if sources:
                    with st.expander("View Verified Sources"):
                        st.dataframe(format_citations(sources), width="stretch")
                
                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
                
            except Exception as e:
                st.error(f"Error generating response: {e}")