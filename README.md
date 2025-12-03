# pharma-sop-rag

Short description
A Retrieval-Augmented Generation (RAG) system for Standard Operating Procedures (SOPs) and pharma documents. Enables indexing of SOPs, semantic search, and generation of concise, sourced answers.

Key goals
- Index SOP documents and related pharma material.
- Answer user queries using retrieved passages with citation.
- Provide a reproducible development and deployment workflow.

Prerequisites
- Python 3.10+ (recommended)
- Git
- An OpenAI-compatible API key (or compatible LLM provider) — set via environment variable
- Vector store (Chroma / FAISS / Weaviate / Pinecone) — per configuration

Quick start
1. Clone the repo:
   git clone <repo-url>
   cd "c:\Users\User\Desktop\Fvr\Orders\Dotter Pharma RAG\pharma-sop-rag"

2. Create virtual environment and install:
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   pip install -r requirements.txt

3. Configure environment variables (example):
   - OPENAI_API_KEY=your_key
   - VECTOR_STORE_TYPE=chroma
   - DATA_DIR=./data/sops

4. Index documents (example script):
   python scripts/index_documents.py --data-dir ./data/sops

5. Run the API (example using FastAPI/uvicorn):
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Usage examples
- Query via API:
  POST /query
  { "question": "How do I perform X in SOP-123?" }

- CLI (if provided):
  python cli/query.py --question "What is the process for Y?"

Configuration
- requirements.txt: Python dependencies
- config/.env or environment vars: API keys, vector store choices, model configuration
- data/: store raw SOPs and source docs (PDFs, Markdown, text)
- index/: persisted vector indices

Recommended architecture notes
- Use chunks with source metadata to allow citations in responses.
- Keep chunk size tuned for the chosen model context window.
- Store document-level metadata (title, source, page) for traceability.
- Apply access controls and logging for any production deployment (PHI / PII considerations).

Development
- Follow feature-branch workflow and open PRs with tests.
- Linting and formatting: flake8 / black (add configs as needed).
- Add unit tests for indexer, retriever, and API endpoints.

Testing
- Add tests under tests/
- Example: pytest -q

Security & compliance
- Do not store unencrypted PHI in plain text.
- Restrict API keys and rotate regularly.
- Review outputs for hallucinations and verify answers against sources before clinical use.

Contributing
- Open an issue to discuss major changes.
- Create a branch per feature/fix and submit a PR.
- Keep commits small and descriptive.

License
- Add or replace with the appropriate license file (e.g., LICENSE).

Contact
- Project maintainer: update CONTACT.md or add maintainer info here.

Notes
- Replace placeholder commands and environment variable names with the actual scripts/config in this repo.
- If a specific vector store or LLM provider is required, document the exact setup and any provider SDK keys.
