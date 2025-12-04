import streamlit as st
import pandas as pd
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import sys

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

load_dotenv()

try:
    from src.rag import FASAEngine
    from src.ingestion import IngestionPipeline
    from src.indexing import IndexingPipeline
except ImportError as e:
    st.error(f"Critical Error: Failed to import FASA modules.\n\nDetails: {e}")
    st.stop()


# PAGE CONFIGURATION
st.set_page_config(
    page_title="FASA | Pharma Regulatory Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Background & Text */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    /* Header Styling */
    .main-header {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: #4A90E2; /* Pharma Blue */
        margin-bottom: 0px;
    }
    
    /* Sub-header / Caption */
    .sub-header {
        font-size: 1.1rem;
        color: #8fa3bf;
        margin-bottom: 2rem;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #2d333b;
    }
    
    /* Button Styling */
    div.stButton > button {
        background-color: #4A90E2;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        transition: background-color 0.3s;
    }
    div.stButton > button:hover {
        background-color: #357ABD;
        border: none;
        color: white;
    }
    
    /* Chat Message Bubbles */
    [data-testid="stChatMessage"] {
        background-color: #1c2128;
        border: 1px solid #30363d;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

if "system_ready" not in st.session_state:
    st.session_state.system_ready = False

if "rag_engine" not in st.session_state:
    with st.spinner("Booting FASA Neural Core..."):
        try:
            # A. Initialize Engines
            st.session_state.rag_engine = FASAEngine()
            st.session_state.ingest_pipe = IngestionPipeline()
            st.session_state.index_pipe = IndexingPipeline()
            
            # B. Initialize Chat History
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            st.session_state.system_ready = True
            
        except Exception as e:
            st.error(f"System Failed to Initialize: {e}")
            st.session_state.system_ready = False

def format_sources(sources_list):
    """
    Converts raw source dictionaries into a clean Pandas DataFrame for display.
    """
    if not sources_list:
        return None
    
    # Flatten the list of dicts
    clean_data = []
    for s in sources_list:
        clean_data.append({
            "SOP Title": s.get("sop_title", "Unknown"),
            "Version": f"v{s.get('version', 'N/A')}",
            "Section ID": s.get("section_id", "N/A"),
            "Section Title": s.get("section_title", "General"),
            "Relevance": f"{s.get('score', 0):.2f}"
        })
    
    df = pd.DataFrame(clean_data)
    df = df.drop_duplicates(subset=["SOP Title", "Section ID"])
    return df

st.markdown("<h1 class='main-header'>FASA: Regulatory AI</h1>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Zero-Hallucination RAG for Pharmaceutical SOPs</div>", unsafe_allow_html=True)

# Guard Clause
if not st.session_state.system_ready:
    st.error("System is offline. Please check your .env configuration and restart.")
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Render citations if they exist
        if "sources" in msg and msg["sources"]:
            with st.expander("Verified Sources"):
                df_sources = format_sources(msg["sources"])
                if df_sources is not None:
                    st.dataframe(df_sources, use_container_width=True, hide_index=True)

if prompt := st.chat_input("Ask about compliance, safety procedures, or responsibilities..."):
    
    # Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Assistant Response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing SOPs & Verifying Claims..."):
            try:
                # Core RAG Logic
                response_payload = st.session_state.rag_engine.query(prompt)
                answer = response_payload["answer"]
                sources = response_payload["sources"]
                print(sources)
                # Display Answer
                st.markdown(answer)
                # Display Sources
                if sources:
                    with st.expander("Verified Sources"):
                        df_sources = format_sources(sources)
                        st.dataframe(df_sources, use_container_width=True, hide_index=True)
                # Save to History
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
            except Exception as e:
                error_msg = f"I encountered an error while processing your request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})