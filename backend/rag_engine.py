from pinecone import Pinecone
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()


class RAGEngine:
    def __init__(self):
        print("Connecting to Pinecone & using Cloud Inference...")
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(os.getenv("PINECONE_INDEX_NAME"))
        print("Connecting to Groq...")
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        print("RAG Engine ready!")

    def get_embedding(self, text: str, input_type: str = "query"):
        response = self.pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[text],
            parameters={"input_type": input_type}
        )
        return response.data[0].values

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Converts spoken audio into text using Groq's hosted Whisper model.
        Used by the /ask-voice endpoint as the first step before running
        the existing RAG answer() pipeline.
        """
        transcription = self.groq.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3",
            response_format="text"
        )
        # response_format="text" returns a plain string directly.
        # If using the default response_format, use transcription.text instead.
        text = transcription if isinstance(transcription, str) else transcription.text
        return text.strip()

    def answer(self, question: str) -> dict:
        query_vector = self.get_embedding(question)
        results = self.index.query(
            vector=query_vector,
            top_k=3,
            include_metadata=True
        )
        chunks = []
        sources = []
        for match in results["matches"]:
            print(f"Score: {match['score']} | Source: {match['metadata'].get('source')}")
            if match["score"] > 0.1:
                chunks.append(match["metadata"].get("text", ""))
                sources.append(match["metadata"].get("source", "Unknown"))

        if not chunks:
            return {
                "answer": "I could not find relevant information to answer your question.",
                "sources": []
            }

        context = "\n\n".join(chunks)
        prompt = f"""You are a helpful AI assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer:"""

        response = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return {
            "answer": response.choices[0].message.content.strip(),
            "sources": list(set(sources))
        }

    def add_document(self, file_path: str, source_name: str) -> int:
        from pdf_processor import PDFProcessor
        processor = PDFProcessor()
        chunks = processor.process(file_path, source_name)

        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = self.get_embedding(chunk["text"], input_type="passage")
            vectors.append({
                "id": f"{source_name}_{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"]
                }
            })

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i:i+batch_size])

        return len(vectors)

    def upload_default_documents(self):
        import uuid
        documents = [
            {"text": "Python is a high-level programming language known for simple syntax. Created by Guido van Rossum in 1991.", "source": "Python Overview"},
            {"text": "Machine learning is a subset of AI that enables computers to learn from data.", "source": "ML Basics"},
            {"text": "FastAPI is a modern Python web framework for building APIs with automatic documentation.", "source": "FastAPI Docs"},
            {"text": "Pinecone is a vector database for AI applications with fast similarity search.", "source": "Pinecone Docs"},
            {"text": "RAG stands for Retrieval Augmented Generation. It combines document retrieval with language model generation.", "source": "RAG Architecture"},
            {"text": "Groq is an AI inference platform providing fast access to LLMs including LLaMA 3.", "source": "Groq Platform"},
            {"text": "Embeddings are numerical vector representations of text used for semantic search.", "source": "Embeddings Guide"},
        ]

        vectors = []
        for doc in documents:
            embedding = self.get_embedding(doc["text"], input_type="passage")
            vectors.append({
                "id": str(uuid.uuid4()),
                "values": embedding,
                "metadata": doc
            })

        self.index.upsert(vectors=vectors)
        print(f"Uploaded {len(vectors)} default documents!")
        return len(vectors)