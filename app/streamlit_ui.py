import streamlit as st
import pandas as pd
import os
import shutil
import time
from pathlib import Path
from dotenv import load_dotenv

# --- Load Environment ---
load_dotenv()

# --- Internal Imports ---
# We connect directly to the backend logic
try:
    from src.rag import FASAEngine
    from src.ingestion import IngestionPipeline
    from src.indexing import IndexingPipeline
except ImportError as e:
    st.error(f"Critical System Error: Could not import FASA modules. {e}")
    st.stop()

# --- Page Config (Enterprise Dark Blue Theme) ---
st.set_page_config(
    page_title="FASA | Pharma Regulatory Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Professional Look ---
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main-header {
        font-size: 2.5rem; 
        color: #4A90E2;
    }
    div.stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "rag_engine" not in st.session_state:
    with st.spinner("🚀 Booting FASA Neural Core..."):
        try:
            # 1. Load RAG Engine (Query Logic)
            st.session_state.rag_engine = FASAEngine()
            
            # 2. Load Pipelines (For UI-based Uploads)
            st.session_state.ingest_pipe = IngestionPipeline()
            st.session_state.index_pipe = IndexingPipeline()
            
            st.session_state.messages = []
            st.session_state.system_ready = True
            
        except Exception as e:
            st.error(f"❌ System Failed to Initialize: {e}")
            st.session_state.system_ready = False

# --- Helper: Format Sources for Display ---
def format_sources(sources_list):
    """
    Converts raw source dictionaries into a clean Pandas DataFrame.
    """
    if not sources_list:
        return None
    
    df = pd.DataFrame(sources_list)
    
    # Rename columns for UI clarity
    column_map = {
        "sop_title": "SOP Title",
        "version": "Version",
        "page": "Page",
        "score": "Relevance",
        "file_name": "File"
    }
    
    # Select and Rename valid columns only
    available_cols = [c for c in column_map.keys() if c in df.columns]
    df = df[available_cols].rename(columns=column_map)
    
    # Drop duplicates (e.g. if 2 chunks come from same page)
    df = df.drop_duplicates(subset=["SOP Title", "Page"])
    
    return df

# =============================================================================
# SIDEBAR: ADMIN & INGESTION
# =============================================================================
with st.sidebar:
    st.title("💊 FASA Control")
    st.caption("v1.0-Demo | Enterprise Mode")
    st.markdown("---")
    
    # 1. LIVE UPLOADER
    st.subheader("📄 SOP Ingestion")
    uploaded_files = st.file_uploader(
        "Upload New SOPs (PDF/DOCX)", 
        accept_multiple_files=True,
        type=["pdf", "docx", "doc"]
    )
    
    if uploaded_files and st.button("🚀 Process & Index Files"):
        if not st.session_state.system_ready:
            st.error("System is not ready.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Create a temp directory for safe processing
            temp_dir = Path("data/temp_uploads")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            total_files = len(uploaded_files)
            success_count = 0
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Processing {i+1}/{total_files}: {file.name}...")
                
                # Save file locally
                file_path = temp_dir / file.name
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                
                try:
                    # A. Run Ingestion (Parsing -> Chunking)
                    nodes = st.session_state.ingest_pipe.run(str(file_path))
                    
                    if nodes:
                        # B. Run Indexing (Vector DB Insert)
                        st.session_state.index_pipe.run(nodes)
                        success_count += 1
                    else:
                        st.warning(f"Skipped {file.name} (No text found)")
                        
                except Exception as e:
                    st.error(f"Failed {file.name}: {e}")
                
                # Cleanup Temp File
                os.remove(file_path)
                progress_bar.progress((i + 1) / total_files)
            
            status_text.success(f"✅ Ingestion Complete! {success_count}/{total_files} indexed.")
            time.sleep(2)
            st.rerun()

    st.markdown("---")
    
    # 2. CHAT CONTROLS
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# =============================================================================
# MAIN: CHAT INTERFACE
# =============================================================================

st.markdown("<h1 class='main-header'>FASA: Regulatory AI</h1>", unsafe_allow_html=True)
st.caption("🔒 Zero Hallucination Mode Active | Citations Enforced")

if not st.session_state.get("system_ready", False):
    st.error("🚨 System is offline. Check database connection or API keys.")
    st.stop()

# 1. RENDER HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # If message has citations, show them
        if msg.get("sources"):
            with st.expander("📚 Verified Sources (Click to Expand)"):
                st.dataframe(format_sources(msg["sources"]), use_container_width=True, hide_index=True)

# 2. INPUT HANDLING
if prompt := st.chat_input("Ask a compliance question about the SOPs..."):
    
    # A. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # B. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("Consulting Vector Database & SOPs..."):
            try:
                # CALL THE RAG ENGINE
                response_payload = st.session_state.rag_engine.query(prompt)
                
                answer = response_payload["answer"]
                sources = response_payload["sources"]
                
                # Display Answer
                st.markdown(answer)
                
                # Display Sources (if any)
                if sources:
                    with st.expander("📚 Verified Sources"):
                        st.dataframe(format_sources(sources), use_container_width=True, hide_index=True)
                
                # Save to History
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
                
            except Exception as e:
                st.error(f"Error generating response: {e}")