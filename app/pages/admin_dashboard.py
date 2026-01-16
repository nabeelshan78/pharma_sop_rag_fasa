import streamlit as st
import pandas as pd
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client.http import models as rest_models

# --- 1. SETUP PATHS & CONFIG ---
# Must be the first Streamlit command
st.set_page_config(
    page_title="FASA Admin | SOP Management",
    page_icon="🛡️",
    layout="wide"
)

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.append(str(project_root))

load_dotenv()

# --- 2. IMPORT MODULES ---
try:
    # Adjust this import based on your actual folder structure
    from src.rag import FASAEngine 
except ImportError:
    # Fallback for testing if module is missing, or stop
    st.error("Could not import FASA Engine. Please check your python path.")
    st.stop()

# --- 3. GLOBAL STYLING ---
st.markdown("""
<style>
    .admin-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #e0e0e0;
        margin-bottom: 0.5rem;
    }
    /* Make the table look cleaner */
    .stDataFrame {
        border: 1px solid #444;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. INITIALIZE ENGINE (Shared State) ---
if "rag_engine" not in st.session_state:
    try:
        with st.spinner("Initializing FASA Engine..."):
            st.session_state.rag_engine = FASAEngine()
    except Exception as e:
        st.error(f"Engine failed to load: {e}")
        st.stop()

# --- 5. BACKEND LOGIC (Your Functions) ---

def update_sop_status(file_name, new_status):
    """
    Directly updates Qdrant Payload (Metadata) without re-embedding.
    """
    if "rag_engine" not in st.session_state:
        st.error("Engine not loaded")
        return 0

    engine = st.session_state.rag_engine
    
    # 1. Access the underlying Qdrant Client directly
    #    (engine -> index -> vector_store -> client)
    client = engine.index.vector_store.client
    collection_name = "fasa_sops"  # Must match your QdrantManager class
    
    status_str = "Active" if new_status else "Inactive"

    # 2. Find points (nodes) related to this file
    #    We filter by "file_name" metadata
    scroll_filter = rest_models.Filter(
        must=[
            rest_models.FieldCondition(
                key="file_name",
                match=rest_models.MatchValue(value=file_name)
            )
        ]
    )

    # 3. Update the payload for these points
    #    This is instant and doesn't cost embedding money/time
    client.set_payload(
        collection_name=collection_name,
        payload={"status": status_str},
        points=scroll_filter
    )
    
    # Optional: Count how many we updated (just for UI feedback)
    # This acts as a sanity check
    points = client.scroll(
        collection_name=collection_name,
        scroll_filter=scroll_filter,
        limit=100  # Adjust if you have massive PDFs
    )[0]
    
    return len(points)


def delete_sop_permanently(file_name):
    """
    Permanently deletes all vectors associated with a specific file from Qdrant.
    WARNING: This action cannot be undone.
    """
    if "rag_engine" not in st.session_state:
        st.error("Engine not loaded")
        return False

    engine = st.session_state.rag_engine
    client = engine.index.vector_store.client
    collection_name = "fasa_sops"
    
    # Define the Filter to match the specific file
    delete_filter = rest_models.Filter(
        must=[
            rest_models.FieldCondition(
                key="file_name",
                match=rest_models.MatchValue(value=file_name)
            )
        ]
    )

    try:
        # Execute Delete Operation
        # points_selector is specific to Qdrant's delete API
        client.delete(
            collection_name=collection_name,
            points_selector=rest_models.FilterSelector(filter=delete_filter)
        )
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False
    

def get_all_sops():
    """
    Retrieves actual metadata from the FASA Engine's index.
    Deduplicates nodes so each file appears only once in the Admin table.
    """
    if "rag_engine" not in st.session_state:
        return pd.DataFrame()
    
    engine = st.session_state.rag_engine
    
    # 2. Access the Qdrant Client directly
    try:
        # Navigate through LlamaIndex to get the native Qdrant client
        # structure: index -> vector_store -> client
        client = engine.index.vector_store.client
        collection_name = "fasa_sops"  # Ensure this matches your ingest config
        
        # 3. Fetch data (Scroll)
        # We fetch up to 10,000 points to ensure we get everything.
        # with_payload=True is crucial to get the metadata.
        response = client.scroll(
            collection_name=collection_name,
            limit=10000, 
            with_payload=True,
            with_vectors=False # We don't need the vectors, just metadata
        )
        points = response[0] # scroll returns (points, offset)
        
    except Exception as e:
        st.error(f"Failed to connect to Qdrant: {e}")
        return pd.DataFrame()
    

    # 4. Process & Deduplicate
    unique_sops = {}

    for point in points:
        meta = point.payload
        if not meta:
            continue
            
        file_name = meta.get("file_name")

        # Deduplication Logic
        if file_name and file_name not in unique_sops:
            status_str = meta.get("status", "Active")
            is_active = True if status_str == "Active" else False

            unique_sops[file_name] = {
                "File Name": file_name,
                "Title": meta.get("sop_title", "Unknown Title"),
                "Doc Number": meta.get("document_number", "---"),
                "Version": meta.get("version_number", "---"),
                "Status": status_str,
                "Active": is_active
            }

    # 5. Return DataFrame
    if not unique_sops:
        return pd.DataFrame(columns=["File Name", "Title", "Doc Number", "Version", "Status", "Active"])
        
    return pd.DataFrame(list(unique_sops.values()))

# --- 6. UI HELPER FUNCTIONS ---

def highlight_inactive(row):
    """
    Pandas Styler: If Status is Inactive, turn text Grey (#888888).
    Otherwise, leave default.
    """
    if row['Status'] == 'Inactive':
        return ['color: #888888'] * len(row)
    else:
        return [''] * len(row)

# --- 7. MAIN DASHBOARD RENDER ---

def render_admin_dashboard():
    # Header
    st.markdown("<div class='admin-header'>🛡️ SOP Knowledge Base Admin</div>", unsafe_allow_html=True)
    st.info("Select an SOP from the list below to modify its visibility to the AI Agent.")

    # 1. Get Data
    df = get_all_sops()

    if df.empty:
        st.warning("No SOPs found in the index.")
        return

    # 2. Main Layout
    # Apply the "Fade" visual effect
    styled_df = df.style.apply(highlight_inactive, axis=1)

    st.caption(f"Total Documents: {len(df)}")

    # 3. Interactive Table
    # on_select="rerun" makes the app reload when a user clicks a row
    event = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",           
        selection_mode="single-row", 
        height=400,
        column_config={
            "Active": None, # st.column_config.Column(hidden=True), # Helper col hidden
            "Status": st.column_config.TextColumn("Current Status")
        }
    )

    
    # 4. Action Panel (Only shows when a row is selected)
    if len(event.selection.rows) > 0:
        selected_index = event.selection.rows[0]
        selected_row = df.iloc[selected_index]
        
        # Extract details
        sel_file = selected_row["File Name"]
        sel_title = selected_row["Title"]
        sel_status = selected_row["Status"]
        sel_is_active = selected_row["Active"]

        # Panel UI
        st.markdown("---")
        st.subheader(f"✏️ Edit / Delete: {sel_title}")
        
        # --- A. EDIT STATUS SECTION ---
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            
            with c1:
                st.markdown(f"**File Name:** `{sel_file}`")
                st.markdown(f"**Doc Number:** {selected_row['Doc Number']}")
            
            with c2:
                new_status_selection = st.radio(
                    "Visibility Status",
                    ["Active", "Inactive"],
                    index=0 if sel_is_active else 1,
                    horizontal=True,
                    key="status_radio",
                    help="Inactive SOPs will be faded in the table and hidden from AI search."
                )
            
            with c3:
                st.write("") # Spacer
                st.write("") 
                
                # Calculate change
                new_is_active_bool = True if new_status_selection == "Active" else False
                has_changed = new_is_active_bool != sel_is_active
                
                if has_changed:
                    if st.button("Confirm Update", type="primary", use_container_width=True):
                        with st.spinner("Updating Metadata..."):
                            count = update_sop_status(sel_file, new_is_active_bool)
                            time.sleep(0.5)
                        st.success(f"Updated {count} nodes!")
                        st.rerun()
                else:
                    st.button("Saved", disabled=True, use_container_width=True)

        # --- B. DANGER ZONE (DELETE) ---
        st.write("")
        # Use an expander to hide the dangerous button by default
        with st.expander("🗑️ Danger Zone: Delete SOP", expanded=False):
            st.error(f"Warning: You are about to permanently delete **{sel_file}**.")
            st.markdown("This will remove the document and all its chunks from the vector database. This action **cannot** be undone.")
            
            col_del_1, col_del_2 = st.columns([4, 1])
            with col_del_2:
                if st.button("Confirm Delete", type="primary"):
                    with st.spinner(f"Deleting {sel_file} from database..."):
                        success = delete_sop_permanently(sel_file)
                        if success:
                            st.toast(f"Deleted {sel_file} successfully!", icon="🗑️")
                            time.sleep(1)
                            st.rerun()

    # # 4. Action Panel (Only shows when a row is selected)
    # if len(event.selection.rows) > 0:
    #     selected_index = event.selection.rows[0]
    #     selected_row = df.iloc[selected_index]
        
    #     # Extract details
    #     sel_file = selected_row["File Name"]
    #     sel_title = selected_row["Title"]
    #     sel_status = selected_row["Status"]
    #     sel_is_active = selected_row["Active"]

    #     # Panel UI
    #     st.markdown("---")
    #     st.subheader(f"✏️ Edit Status: {sel_title}")
        
    #     # Create a container for the edit form
    #     with st.container(border=True):
    #         c1, c2, c3 = st.columns([2, 2, 1])
            
    #         with c1:
    #             st.markdown(f"**File Name:** `{sel_file}`")
    #             st.markdown(f"**Doc Number:** {selected_row['Doc Number']}")
            
    #         with c2:
    #             # The Toggle Mechanism (Radio Button)
    #             new_status_selection = st.radio(
    #                 "Visibility Status",
    #                 ["Active", "Inactive"],
    #                 index=0 if sel_is_active else 1,
    #                 horizontal=True,
    #                 help="Inactive SOPs will be faded in the table and hidden from AI search."
    #             )
            
    #         with c3:
    #             # Logic to enable/disable button
    #             new_is_active_bool = True if new_status_selection == "Active" else False
    #             has_changed = new_is_active_bool != sel_is_active
                
    #             st.write("") # Spacer to align button
    #             st.write("") 
                
    #             if has_changed:
    #                 confirm_btn = st.button("✅ Confirm Update", type="primary", use_container_width=True)
    #                 if confirm_btn:
    #                     with st.spinner("Updating Metadata..."):
    #                         count = update_sop_status(sel_file, new_is_active_bool)
    #                         time.sleep(0.5) # UX pause
    #                     st.success(f"Updated {count} nodes to {new_status_selection}!")
    #                     st.rerun()
    #             else:
    #                 st.button("No Changes", disabled=True, use_container_width=True)

# --- 8. RUN APP ---
if __name__ == "__main__":
    render_admin_dashboard()


    















# import streamlit as st
# import pandas as pd
# import sys
# from pathlib import Path
# from dotenv import load_dotenv
# import time

# # --- SETUP PATHS ---
# current_file = Path(__file__).resolve()
# project_root = current_file.parent.parent
# sys.path.append(str(project_root))

# load_dotenv()

# # --- IMPORT YOUR MODULES ---
# try:
#     from src.rag import FASAEngine
# except ImportError:
#     st.error("Could not import FASA Engine. Check your path.")
#     st.stop()

# # --- PAGE CONFIG ---
# st.set_page_config(
#     page_title="FASA Admin | SOP Management",
#     page_icon="🛡️",
#     layout="wide"
# )

# # --- STYLING ---
# st.markdown("""
# <style>
#     .admin-header {
#         font-size: 2.5rem;
#         font-weight: 700;
#         color: #e0e0e0;
#         margin-bottom: 0.5rem;
#     }
#     .stDataFrame {
#         border: 1px solid #30363d;
#         border-radius: 5px;
#     }
# </style>
# """, unsafe_allow_html=True)

# st.markdown("<div class='admin-header'>🛡️ SOP Knowledge Base Admin</div>", unsafe_allow_html=True)
# st.info("Manage the active status of Standard Operating Procedures visible to the AI.")

# # --- INITIALIZE ENGINE (Shared State) ---
# if "rag_engine" not in st.session_state:
#     try:
#         st.session_state.rag_engine = FASAEngine()
#     except Exception as e:
#         st.error(f"Engine failed to load: {e}")
#         st.stop()




# import streamlit as st
# import pandas as pd

# # --- Your Existing Backend Functions (Kept Unchanged) ---
# def update_sop_status(file_name, new_status):
#     """Updates metadata in index."""
#     if "rag_engine" not in st.session_state:
#         st.error("RAG Engine not loaded.")
#         return 0
        
#     engine = st.session_state.rag_engine
#     all_nodes = engine.index.docstore.docs.values()
#     status_str = "Active" if new_status else "Inactive"
#     count = 0
#     nodes_to_update = []

#     for node in all_nodes:
#         if node.metadata.get("file_name") == file_name:
#             node.metadata["status"] = status_str
#             nodes_to_update.append(node)
#             count += 1
    
#     if nodes_to_update:
#         engine.index.docstore.add_documents(nodes_to_update, allow_update=True)
#         if hasattr(engine.index.storage_context, "persist"):
#             engine.index.storage_context.persist()
            
#     return count

# def get_all_sops():
#     """Retrieves metadata (Kept exactly as you provided)."""
#     if "rag_engine" not in st.session_state:
#         return pd.DataFrame()
#     engine = st.session_state.rag_engine
#     try:
#         all_nodes = engine.index.docstore.docs.values()
#     except AttributeError:
#         return pd.DataFrame()

#     unique_sops = {}
#     for node in all_nodes:
#         meta = node.metadata
#         file_name = meta.get("file_name")
#         if file_name and file_name not in unique_sops:
#             status_str = meta.get("status", "Active")
#             is_active = True if status_str == "Active" else False
#             unique_sops[file_name] = {
#                 "File Name": file_name,
#                 "Title": meta.get("sop_title", "Unknown Title"),
#                 "Doc Number": meta.get("document_number", "---"),
#                 "Version": meta.get("version_number", "---"),
#                 "Status": status_str,
#                 "Active": is_active
#             }
#     if not unique_sops:
#         return pd.DataFrame(columns=["File Name", "Title", "Doc Number", "Version", "Status", "Active"])
#     return pd.DataFrame(list(unique_sops.values()))

# # --- NEW: Admin UI Logic ---

# def highlight_inactive(row):
#     """
#     Pandas Styler function. 
#     If Status is Inactive, turn text Grey (#aaaaaa).
#     Otherwise, leave default.
#     """
#     if row['Status'] == 'Inactive':
#         return ['color: #aaaaaa'] * len(row)
#     else:
#         return [''] * len(row)

# def render_admin_dashboard():
#     st.title("🎛️ SOP Admin Control")

#     # 1. Get Data
#     df = get_all_sops()

#     if df.empty:
#         st.info("No SOPs found in the index.")
#         return

#     # 2. Setup Columns (Table on Left, Action Panel on Right/Bottom)
#     st.caption("Select a row to edit its status.")

#     # Apply the "Fade" visual effect
#     styled_df = df.style.apply(highlight_inactive, axis=1)

#     # 3. Render Table with Selection Enabled
#     # user selects a row, we get the index back
#     event = st.dataframe(
#         styled_df,
#         use_container_width=True,
#         hide_index=True,
#         on_select="rerun",           # This triggers the reload on click
#         selection_mode="single-row", # Only allow one SOP edit at a time
#         column_config={
#             "Active": st.column_config.Column(hidden=True) # Hide the boolean helper col
#         }
#     )

#     # 4. The "Admin Action Panel"
#     # This block only runs if a row is selected
#     if len(event.selection.rows) > 0:
#         selected_index = event.selection.rows[0]
#         selected_row = df.iloc[selected_index]
        
#         selected_file = selected_row["File Name"]
#         current_status = selected_row["Status"]
#         is_active = selected_row["Active"]

#         st.divider()
#         st.subheader(f"🛠️ Editing: {selected_row['Title']}")
        
#         c1, c2 = st.columns([1, 2])
        
#         with c1:
#             st.write(f"**File:** `{selected_file}`")
#             st.write(f"**Current Status:** {current_status}")

#         with c2:
#             # The Toggle/Switch Mechanism
#             # We use a radio or segmented control for clear "Admin" feel
#             new_status_selection = st.radio(
#                 "Set Status:",
#                 ["Active", "Inactive"],
#                 index=0 if is_active else 1,
#                 horizontal=True
#             )
            
#             # Determine if changes are needed
#             new_is_active = True if new_status_selection == "Active" else False
#             has_changed = new_is_active != is_active

#             # The "Confirm Changes" Button
#             if has_changed:
#                 confirm_btn = st.button(
#                     f"Confirm Change to {new_status_selection}", 
#                     type="primary",
#                     use_container_width=True
#                 )
                
#                 if confirm_btn:
#                     with st.spinner("Updating Index Metadata..."):
#                         count = update_sop_status(selected_file, new_is_active)
#                         st.success(f"Updated {count} chunks. Status is now {new_status_selection}.")
#                         st.rerun() # Refresh table immediately to show new color
#             else:
#                 st.button("No Changes Detected", disabled=True, use_container_width=True)

# # Run the dashboard
# render_admin_dashboard()




# # --- MAIN UI ---

# # 1. Load Data
# if "sop_df" not in st.session_state:
#     st.session_state.sop_df = get_all_sops()

# # 2. Controls
# col1, col2 = st.columns([4, 1])
# with col1:
#     filter_text = st.text_input("🔍 Filter by Title or Number", placeholder="Type to search...")
# with col2:
#     st.markdown("<br>", unsafe_allow_html=True) # Spacer
#     if st.button("🔄 Refresh Data"):
#         st.session_state.sop_df = get_all_sops()
#         st.rerun()

# # 3. Filter Logic
# df_view = st.session_state.sop_df.copy()
# if filter_text:
#     mask = df_view.astype(str).apply(lambda x: x.str.contains(filter_text, case=False)).any(axis=1)
#     df_view = df_view[mask]

# # 4. EDITABLE DATA TABLE
# # This is the magic component that allows the toggle
# edited_df = st.data_editor(
#     df_view,
#     column_config={
#         "Status": st.column_config.CheckboxColumn(
#             "AI Active",
#             help="Uncheck to hide this SOP from RAG results",
#             default=True,
#         ),
#         "File Name": st.column_config.TextColumn("File Name", disabled=True),
#         "Title": st.column_config.TextColumn("SOP Title", disabled=True),
#         "Doc Number": st.column_config.TextColumn("Doc #", disabled=True),
#         "Revision": st.column_config.TextColumn("Rev", disabled=True),
#     },
#     disabled=["File Name", "Title", "Doc Number", "Revision"], # Only Status is editable
#     hide_index=True,
#     use_container_width=True,
#     height=500
# )

# # 5. Save Changes Logic
# # Compare original vs edited to find changes
# if st.button("💾 Save Changes", type="primary"):
#     # In the future, this is where you write to your DB/VectorStore
#     st.session_state.sop_df = edited_df
    
#     # Logic to identify what changed (for backend processing)
#     # This loop is just a placeholder to show you how to detect the "False" rows
#     inactive_count = len(edited_df[edited_df["Status"] == False])
    
#     st.success(f"Configuration updated! {inactive_count} SOPs are now marked as Inactive.")
#     time.sleep(1)
#     st.rerun()