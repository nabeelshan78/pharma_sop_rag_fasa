Pharma SOP RAG
--------------
Lightweight repository skeleton for a SOP retrieval-augmented-generation (RAG) pipeline for pharmaceutical SOP documents.

Structure:
- data/: raw/processed vectors
- src/: python package with ingestion, indexing, rag, utils
- app.py: simple CLI pipeline runner
- main_api.py: FastAPI entrypoint

Quick start:
1. Create a virtualenv and install requirements.txt
2. Populate data/raw_sops with SOP files
3. Implement/adjust components in src/ as needed
