import re
import fitz
import os

def clean_text(text: str) -> str:
    """
    Applies Regex cleaning rules to remove noise (headers, footers, pagination).
    """
    noise_patterns = [
        r"_n_", 
        r"GRUNENTHAL",
        r"^\s*page\s*$" 
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)
    
    header_keywords = [
        r"Number:.*", 
        r"Nummer:.*", 
        r"Numero:.*", 
        r"Número:.*", 
        r"Revision:.*", 
        r"Revisione:.*", 
        r"Revisão:.*", 
        r"Revisión:.*", 
        r"Status:.*", 
        r"Estado:.*", 
        r"Effective Date:.*",
        r"Data Effettiva:.*",
        r"Data Efetiva:.*",
        r"Fecha efectiva:.*",
        r"Gültigkeitsdatum:.*",
        r"Document No:.*",
        r"Local Title:.*",
        r"Lokaler Titel:.*",
        r"Titolo locale:.*",
        r"Título Local:.*",
        r"Release.*"
    ]
    for pattern in header_keywords:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    footer_patterns = [
        r"(This is an uncontrolled copy valid for.*)",
        r"(Page \d+ of \d+)"
    ]
    for pattern in footer_patterns:
        match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = text[:match.start()]

    text = re.sub(r"\b\d+\s+of\s+\d+\b", "", text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()








if __name__ == "__main__":
    # REPLACE THIS with the path to your English SOP
    # pdf_path = r"C:\Users\User\Desktop\Fvr\Orders\Dotter\pharma_sop_rag_fasa\data\raw_sops\GRT_PROC_English_stamped_Rev06.docmNov302025052119.pdf"
    # pdf_path = r"C:\Users\User\Desktop\Fvr\Orders\Dotter\pharma_sop_rag_fasa\data\raw_sops\GRT_PROC_English_stamped_Rev07 (1).docxNov302025024526.pdf"
    pdf_path = r"C:\Users\User\Desktop\Fvr\Orders\Dotter\pharma_sop_rag_fasa\data\lang_sops\GRT_PROC_Spanish_stamped_Rev06 (2).docxDec192025021700.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found at {pdf_path}")
    else:
        print(f"📘 Processing: {os.path.basename(pdf_path)}\n")
        
        try:
            doc = fitz.open(pdf_path)
            
            for i, page in enumerate(doc):
                # Standard Logic: Skip Cover Page (Page 1 / Index 0)
                if i == 0: 
                    print(f"--- [Skipping Cover Page (Page {i+1})] ---\n")
                    continue
                
                # Extract raw text
                raw_text = page.get_text("text")
                
                # Apply Cleaning
                cleaned_output = clean_text(raw_text)
                
                # Print Result for visual verification
                if i > 10:
                    break  # Limit to first 10 pages for brevity
                print(f"--- [Page {i+1}] ---")
                print(cleaned_output)
                print("-" * 40 + "\n")
                
            doc.close()
            print("✅ Done processing.")
            
        except Exception as e:
            print(f"Error processing PDF: {e}")