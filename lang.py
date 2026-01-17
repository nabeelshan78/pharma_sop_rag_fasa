import fitz  # PyMuPDF
from langdetect import detect, DetectorFactory, LangDetectException
import os
import glob

# CRITICAL: Set seed for consistent results
DetectorFactory.seed = 0 

def detect_language(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return None, "error"

    total_pages = len(doc)
    
    # --- STEP 1: Detect Language (Using Pages 2 & 3 only) ---
    sample_text = ""
    # pages_to_sample = []
    
    # # We want index 1 (Page 2) and index 2 (Page 3)
    # if total_pages > 1: pages_to_sample.append(1) 
    # if total_pages > 2: pages_to_sample.append(2) 
    
    # Extract text from sample pages
    for p_idx in [1, 2]:
        sample_text += doc[p_idx].get_text()
        
    # Detect
    detected_lang = "unknown"
    try:
        # If we have enough text on p2/3, detect it
        if len(sample_text.strip()) > 50:
            detected_lang = detect(sample_text) 
        # FALLBACK: If p2/3 are empty (or file only has 1 page), try Page 1?
        # If you strictly want to ignore Page 1, leave this as is. 
        # If you want to fallback to Page 1 for detection only:
        elif total_pages == 1:
             fallback_text = doc[0].get_text()
             if len(fallback_text.strip()) > 50:
                 detected_lang = detect(fallback_text)
             else:
                 detected_lang = "en" # Absolute fallback
        else:
            detected_lang = "en" # Default if p2/3 exist but have no text (images)
            
    except LangDetectException:
        detected_lang = "unknown"

    print(f"File: {os.path.basename(pdf_path)} | Detected Language: {detected_lang}")
    return detected_lang

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # REPLACE THIS with your actual folder path
    folder_path = "data/lang_sops"
    
    # Get all PDFs in the folder
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {folder_path}")
    else:
        print(f"Found {len(pdf_files)} PDFs. Processing...\n")
        print("-" * 60)
        
        results = []
        for pdf_file in pdf_files:
            lang = detect_and_process_pdf(pdf_file)