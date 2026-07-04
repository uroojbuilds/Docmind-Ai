from rag_engine import RAGEngine

if __name__ == "__main__":
    rag = RAGEngine()
    count = rag.upload_default_documents()
    print(f"Done! {count} documents uploaded to Pinecone.")