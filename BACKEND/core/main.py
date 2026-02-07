import os
import base64
# 1. Added 'Form' to imports so we can receive the Session ID with the audio file
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles   # Added for UI
from fastapi.responses import FileResponse    # Added for UI
from pydantic import BaseModel

# --- IMPORTS ---
import voice_engine as ve
from query_engine import generate_answer

app = FastAPI(title="VedaBuddy API")

# ==========================================
#  CORS SETUP (Allow Frontend Access)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Models ---
class ChatRequest(BaseModel):
    question: str
    # Default is "web_user_1", but Frontend will now send a random ID to override this
    session_id: str = "web_user_1"

# NEW: Request Model for the Voice Chat (Text Input -> Voice Output)
class VoiceChatRequest(BaseModel):
    text: str
    session_id: str = "voice_user"

# ==========================================
#  ENDPOINT 1: INITIAL GREETING (Voice Mode Start)
# ==========================================
@app.get("/greeting")
async def get_greeting():
    """
    Triggered when user clicks the Mic icon.
    Returns: { text: "Good Morning...", audio: "base64..." }
    """
    # 1. Generate Text
    text = ve.get_llm_greeting()
    
    # 2. Generate Audio
    audio_bytes = ve.generate_voice(text)
    
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate greeting audio")
    
    # 3. Encode to Base64 for easy Frontend playback
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    return {
        "text": text,
        "audio": f"data:audio/mp3;base64,{audio_b64}"
    }

# ==========================================
#  ENDPOINT 2A: TRANSCRIBE ONLY (Fast)
# ==========================================
@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """
    STEP 1: Listen to the user.
    Returns the text IMMEDIATELY so the UI can show it.
    """
    try:
        audio_bytes = await file.read()
        user_query = ve.transcribe_audio(audio_bytes)
        
        if not user_query:
            return {"error": "I couldn't hear anything clearly."}
        
        print(f"DEBUG: Transcribed -> {user_query}")
        return {"transcript": user_query}

    except Exception as e:
        print(f"Transcribe Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
#  ENDPOINT 2B: CHAT & VOICE GENERATION (Slow)
# ==========================================
@app.post("/chat-voice")
async def chat_voice_endpoint(request: VoiceChatRequest):
    """
    STEP 2: Think & Speak.
    Takes the text from Step 1, generates RAG answer, and creates Audio.
    """
    try:
        user_query = request.text
        session_id = request.session_id

        print(f"DEBUG: Processing Query -> {user_query} for Session -> {session_id}")

        # 1. Level 1 LLM (RAG / The Brain)
        full_rag_answer = generate_answer(user_query, session_id=session_id)
        
        # 2. Level 2 LLM (The Performer - Script for TTS)
        voice_script = ve.make_answer_listenable(full_rag_answer)
        
        # 3. TTS (ElevenLabs) - "The Mouth"
        audio_out_bytes = ve.generate_voice(voice_script)
        
        # Encode Response
        audio_b64 = None
        if audio_out_bytes:
            audio_b64 = base64.b64encode(audio_out_bytes).decode("utf-8")

        return {
            "chat_answer": full_rag_answer, # For Chat History
            "voice_script": voice_script,   # Debugging
            "audio": f"data:audio/mp3;base64,{audio_b64}" if audio_b64 else None
        }

    except Exception as e:
        print(f"Chat-Voice Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
#  ENDPOINT 3: STANDARD CHAT (Text Fallback)
# ==========================================
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Standard RAG chat for the text box."""
    # This already uses request.session_id, so it works automatically 
    # once the frontend sends the new ID.
    answer = generate_answer(request.question, session_id=request.session_id)
    return {"answer": answer}

# ==========================================
#  FINAL UI SERVING (THE FIX FOR ASSETS)
# ==========================================
# HARDCODED ABSOLUTE PATH (Point exactly to your dist folder)
FRONTEND_PATH = r"F:\RAG VEDABUDDY voice assistant\FRONTEND\dist"

print(f"DEBUG: Looking for UI files at -> {FRONTEND_PATH}")

if os.path.exists(FRONTEND_PATH):
    print("SUCCESS: UI 'dist' folder found. Serving VedaBuddy UI.")
    
    # CATCH-ALL MOUNT:
    # This mounts the ENTIRE dist folder to the root URL ("/")
    # This ensures that main-bg.mp4, sphere.gif, and index.html are ALL accessible.
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="ui")

else:
    # If the folder is missing, print a warning
    print(f"CRITICAL ERROR: The folder '{FRONTEND_PATH}' does not exist.")

# Run with: python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)