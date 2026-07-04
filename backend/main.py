from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_engine import RAGEngine
import os
app = FastAPI(title="RAG Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://docmindaichatbot.netlify.app"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
rag = RAGEngine()
class QuestionRequest(BaseModel):
    question: str
class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
class VoiceAnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
@app.get("/")
def root():
    return {"message": "RAG Chatbot is running!"}
@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    result = rag.answer(request.question)
    return AnswerResponse(answer=result["answer"], sources=result["sources"])
@app.post("/ask-voice", response_model=VoiceAnswerResponse)
async def ask_voice(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    try:
        transcript = rag.transcribe_audio(audio_bytes, filename=file.filename or "audio.webm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Could not detect any speech in the audio")
    result = rag.answer(transcript)
    return VoiceAnswerResponse(question=transcript, answer=result["answer"], sources=result["sources"])
@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    count = rag.add_document(file_path, file.filename)
    return {"message": f"Uploaded and indexed {count} chunks from {file.filename}"}
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))  # ✅ 8080
    uvicorn.run(app, host="0.0.0.0", port=port)