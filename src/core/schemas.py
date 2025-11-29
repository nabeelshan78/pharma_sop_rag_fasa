from pydantic import BaseModel, Field
from typing import List, Optional

class SOPMetadata(BaseModel):
    """
    Standardizes metadata extracted during Ingestion.
    """
    sop_name: str
    version: str
    section: str = "General"
    page_numbers: str = "N/A"
    filename: str

class RetrievalSource(BaseModel):
    """
    Standardizes the source citation returned to the UI.
    """
    sop_name: str
    version: str
    page: str
    section: str
    score: float = 0.0
    text_preview: Optional[str] = None

class RAGResponse(BaseModel):
    """
    Final object returned by the RAG Engine.
    """
    answer: str
    sources: List[RetrievalSource]