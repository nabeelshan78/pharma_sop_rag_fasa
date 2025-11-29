from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Pharma SOP RAG API")

class QARequest(BaseModel):
    question: str

@app.post("/qa")
def qa(req: QARequest):
    # Placeholder implementation: replace with Retriever + Generator assembly
    return {"answer": "This is a placeholder. Implement retriever + generator to get real answers."}
