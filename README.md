# Pharmaceutical SOP RAG System Setup (FASA)

# ollama pull nomic-embed-text-v2-moe / nomic-embed-text

This is a local Retrieval-Augmented Generation (RAG) system designed for Pharmaceutical Regulatory assistance. It ingests Standard Operating Procedures (SOPs), indexes them into a vector database, and uses a local Large Language Model (LLM) to answer questions without data leaving your machine.

## System Architecture
- **Language:** Python 3.11
- **Interface:** Streamlit
- **Vector Database:** Qdrant (Dockerized)
- **LLM Engine:** Ollama (Local)
- **Models:** 
  - LLM: `llama3.1:8b`
  - Embeddings: `nomic-embed-text-v2-moe`

---

## Prerequisites

Before starting, ensure you have the following installed:

1.  **Python (3.11 or higher)
2.  **Docker Desktop:** Required to run the database.
3.  **Ollama:** Required to run the AI models locally. [Download Ollama](https://ollama.com/download)

---


## Step 0: AI Model Setup (Ollama)

The code is specifically configured to use specific models. You must download these versions for the system to work.

1. Download and run the executable installer from this link `https://ollama.com/download`

2. Verification: Once installed, open your terminal and run: `ollama --version`
If the version number appears, the engine is ready. The server runs automatically in the background on port 11434.

3. Pull the required AI models:

   - Embedding model (for vector search):
     ```bash
     ollama pull nomic-embed-text-v2-moe
     ```

   - Language model (for answering questions):
     ```bash
     ollama pull llama3.1:8b
     ```

4. # Quick check after pulling
Run in CMD `ollama list`

---


## Step 1: Project Installation

1.  Open your terminal (Command Prompt, PowerShell, or Terminal).
2.  Navigate to the project folder.
3.  Create a virtual environment to keep dependencies isolated:
    ```bash
    python -m venv venv
    ```
4.  Activate the virtual environment:
    *   **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    *   **Mac/Linux:**
        ```bash
        source venv/bin/activate
        ```
5.  Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

---

## Step 2: Infrastructure Setup (Qdrant)

We use Qdrant to store the mathematical representations (vectors) of your SOPs.

1.  Ensure Docker Desktop is running.
2.  In your terminal (at the project root), start the database:
    ```bash
    docker-compose up -d
    ```
3.  Verify it is running by visiting [http://localhost:6333/dashboard](http://localhost:6333/dashboard) in your browser. You should see the Qdrant dashboard.

---

## Step 3: Configuration

Ensure your `.env` file exists in the root directory and contains the following settings:

```bash
QDRANT_URL=http://localhost:6333
OLLAMA_BASE_URL=http://localhost:11434
HYBRID_ALPHA=0.8
```

## Step 4: Data Ingestion
Run the bulk ingestion script from the project root: `python .\scripts\bulk_ingest.py`

## Step 5: Running the Application
Run the Streamlit app: `streamlit run .\app\app.py`

A browser window will automatically open (usually at http://localhost:8501).
Wait for the "Booting FASA Neural Core..." message to finish.

Type your query into the chat box.