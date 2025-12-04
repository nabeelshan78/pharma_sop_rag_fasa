import streamlit as st
import pandas as pd
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import sys

# -----------------------------------------------------------------------------
# 1. PATH CONFIGURATION (CRITICAL)
# -----------------------------------------------------------------------------
# Ensures Python can find the 'src' package when running from 'app/'
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

# -----------------------------------------------------------------------------
# 2. ENVIRONMENT & IMPORTS
# -----------------------------------------------------------------------------
load_dotenv()

try:
    from src.rag import FASAEngine
    from src.ingestion import IngestionPipeline
    from src.indexing import IndexingPipeline
except ImportError as e:
    st.error(f"Critical Error: Failed to import FASA modules.\n\nDetails: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 3. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FASA | Pharma Regulatory Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 4. CUSTOM CSS (Enterprise Dark Blue Theme)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 5. SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 6. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
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
    
    # Remove duplicates based on Section ID to avoid spam
    df = df.drop_duplicates(subset=["SOP Title", "Section ID"])
    return df

# # =============================================================================
# # 7. SIDEBAR: ADMIN CONTROLS
# # =============================================================================
# with st.sidebar:
#     st.image("https://placehold.co/200x80/0e1117/4A90E2?text=FASA+AI", use_column_width=True)
#     st.title("Admin Console")
#     st.markdown("---")
    
#     # --- Live Ingestion ---
#     st.subheader("Upload SOPs")
#     uploaded_files = st.file_uploader(
#         "Upload PDF/DOCX files for immediate indexing.", 
#         accept_multiple_files=True,
#         type=["pdf", "docx", "doc", "docm"]
#     )
    
#     if uploaded_files and st.button("Process & Index Files"):
#         if not st.session_state.system_ready:
#             st.error("System is not initialized.")
#         else:
#             progress_bar = st.progress(0)
#             status_text = st.empty()
            
#             # Create temp directory
#             temp_dir = Path("data/temp_uploads")
#             temp_dir.mkdir(parents=True, exist_ok=True)
            
#             total_files = len(uploaded_files)
#             success_count = 0
            
#             for i, file in enumerate(uploaded_files):
#                 status_text.text(f"Processing {i+1}/{total_files}: {file.name}...")
                
#                 # Save locally
#                 file_path = temp_dir / file.name
#                 with open(file_path, "wb") as f:
#                     f.write(file.getbuffer())
                
#                 try:
#                     # 1. Ingest (Loader -> Cleaner -> Chunker)
#                     nodes = st.session_state.ingest_pipe.run(str(file_path))
                    
#                     if nodes:
#                         # 2. Index (Vector DB)
#                         st.session_state.index_pipe.run(nodes)
#                         success_count += 1
#                     else:
#                         st.warning(f"Skipped {file.name} (No content extracted)")
                        
#                 except Exception as e:
#                     st.error(f"Failed {file.name}: {e}")
                
#                 # Cleanup
#                 if file_path.exists():
#                     os.remove(file_path)
                
#                 progress_bar.progress((i + 1) / total_files)
            
#             status_text.success(f"Completed! {success_count}/{total_files} files indexed.")
#             time.sleep(2)
#             st.rerun() # Refresh to allow searching new data immediately

#     st.markdown("---")
    
#     # --- History Management ---
#     if st.button("Clear Chat History"):
#         st.session_state.messages = []
#         st.rerun()
        
#     st.markdown("---")
#     st.caption("FASA v1.0.0 | Enterprise Edition")

# =============================================================================
# 8. MAIN CHAT INTERFACE
# =============================================================================

st.markdown("<h1 class='main-header'>FASA: Regulatory AI</h1>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Zero-Hallucination RAG for Pharmaceutical SOPs</div>", unsafe_allow_html=True)

# Guard Clause
if not st.session_state.system_ready:
    st.error("System is offline. Please check your .env configuration and restart.")
    st.stop()

# A. Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Render citations if they exist
        if "sources" in msg and msg["sources"]:
            with st.expander("Verified Sources"):
                df_sources = format_sources(msg["sources"])
                if df_sources is not None:
                    st.dataframe(df_sources, use_container_width=True, hide_index=True)

# B. Handle User Input
if prompt := st.chat_input("Ask about compliance, safety procedures, or responsibilities..."):
    
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate Assistant Response
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