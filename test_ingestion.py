from src.ingestion import IngestionPipeline

# Point to a real file you have
file_path = "data/raw_sops/GRT_PROC_English_stamped_Rev07 (1).docxNov302025024526.pdf"

pipeline = IngestionPipeline()
nodes = pipeline.run(file_path)

if nodes:
    # first 5
    for i, node in enumerate(nodes[:5]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Text:\n{node.text}")
        print(f"Metadata:\n{node.metadata}")
        print("="*50)