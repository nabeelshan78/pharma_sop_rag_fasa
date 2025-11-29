from pydantic import BaseModel
from typing import List, Optional

class SOPDocument(BaseModel):
    id: str
    title: Optional[str] = None
    text: str

class DocumentChunk(BaseModel):
    id: str
    sop_id: str
    chunk_index: int
    text: str
    metadata: dict = {}
