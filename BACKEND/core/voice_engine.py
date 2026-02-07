import os
import io
import datetime
import re
import random
from groq import Groq
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

# 1. Setup & Environment
# FIX: 'override=True' forces Python to read the NEW key from .env every time.
load_dotenv(override=True)

# Initialize Clients
# Ensure your .env has GROQ_API_KEY and ELEVENLABS_API_KEY
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Configuration Constants
# We stick to V3 for best accuracy with Ayurvedic terms (Vata, Pitta, etc.)
STT_MODEL = "whisper-large-v3"       
EMOTION_MODEL = "llama-3.1-8b-instant" # Groq's fast inference model
TTS_MODEL = "eleven_turbo_v2_5"      # ElevenLabs Low Latency
VOICE_ID = "5mnzuCX5VBUY3U7RY1pn"    # Bella (Change if needed)
# EXAVITQu4vr4xnSDxMaL
# ==========================================
#  LOGIC 1: DYNAMIC GREETING (LLM BASED)
# ==========================================

def get_llm_greeting():
    """Generates a dynamic greeting based on time of day."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        time_context = "morning"
    elif 12 <= hour < 17:
        time_context = "afternoon"
    else:
        time_context = "evening"

    # RANDOMIZER: This forces the AI to change the greeting every time
    vibes = [
        "enthusiastic and energetic",
        "calm and peaceful",
        "wise and ancient",
        "cheerful and friendly",
        "warm and inviting"
    ]
    selected_vibe = random.choice(vibes)

    # UPDATED PROMPT: Includes your specific intro & randomness
    prompt = (
        f"You are KARUNA AI. Generate a spoken greeting for the {time_context}. "
        f"VIBE: {selected_vibe}. "
        f"REQUIREMENTS:\n"
        f"1. Start with a variation of 'Good {time_context} friend' or 'Welcome seeker'.\n"
        f"2. You MUST say exactly this phrase in the middle: 'I am Karuna AI, your smart voice assistant for Ayurveda'.\n"
        f"3. End by asking 'How are you today?' or 'How can I help you balance your health?'.\n"
        f"4. Keep it under 20 words total."
    )
    
    try:
        response = groq_client.chat.completions.create(
            model=EMOTION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, # Max creativity
            max_tokens=60
        )
        return response.choices[0].message.content.replace('"', '')
    except Exception as e:
        print(f"Greeting Error: {e}")
        # Fallback that matches your requested style
        return f"Good {time_context} friend! I am VedaBuddy, your smart voice assistant for Ayurveda. How are you today?"

# ==========================================
#  LOGIC 2: SPEECH TO TEXT (STT) - EAR
# ==========================================

def transcribe_audio(audio_bytes):
    """
    Converts audio bytes (from browser) -> Text (via Groq Whisper).
    """
    if not audio_bytes:
        return None
    try:
        # Create a virtual file in memory with a filename
        # Groq requires a 'filename' attribute to know it's audio
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "input.wav" 

        transcription = groq_client.audio.transcriptions.create(
            file=audio_file, 
            model=STT_MODEL,
            response_format="text",
            language="en" # Force English for consistency
        )
        return transcription.strip()
    except Exception as e:
        print(f"STT Error: {e}")
        return None

# ==========================================
#  LOGIC 3: THE EMOTION WRAPPER (LEVEL 2 LLM)
# ==========================================

def make_answer_listenable(detailed_text: str):
    """
    LEVEL 2: Takes the Level 1 (RAG) long answer and converts it 
    into a short, human-like script for TTS.
    """
    # YOUR REFINED PROMPT (Strictly fixed for Identity & Direct Answers)
    system_prompt = (
        "You are the voice of Karuna AI, an expert Ayurvedic Doctor (Vaidya).\n"
        "TASK: Summarize the provided text into 2-3 spoken sentences (max 40 words) for the patient.\n"
        "CORE RULES:\n"
        "1. PRESERVE INTENT: If the input is a diagnosis ('You have Vata'), say it clearly. If it is 'Bye', say 'Bye'. Do not add new info. Do not remove the main answer.\n"
        "2. CONCISENESS: Condense the text to max 40 words. Keep the most important fact/instruction.\n"
        "3. PERSPECTIVE FIX: The input text talks ABOUT the user. You are speaking TO the user. \n"
        "4. DOCTOR PERSONA: Convert 'I' symptoms to 'You'. (e.g., Text: 'I feel bloated' -> Voice: 'If you feel bloated'). Never speak as the patient.\n"
        "5. You don't have to change the meaning just make the answer in short spoken form while not changing the actual impact and meaning.\n"
        
        "CRITICAL RULES FOR STYLE:\n"
        "1. Warm and Professional. No 'honey', 'baby', 'dear'.\n"
        "2. No Lists/Bullet points. Speak in flow.\n"
        "3. Keep it under 40 words."
        "5. PRESERVE MEANING: Do not change the meaning of the provided text."
    )

    try:
        response = groq_client.chat.completions.create(
            model=EMOTION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": detailed_text}
            ],
            temperature=0.6, # Slightly lower temp for more professional adherence
            max_tokens=150
        )
        script = response.choices[0].message.content
        
        # Cleanup: Remove any rogue brackets or asterisks (Just in case)
        clean_script = re.sub(r'\[.*?\]', '', script) 
        clean_script = clean_script.replace('*', '')  
        return clean_script.strip()

    except Exception as e:
        print(f"Emotion Wrapper Error: {e}")
        # Fallback: Just return the first 2 sentences of the original text
        return ". ".join(detailed_text.split(".")[:2]) + "."

# ==========================================
#  LOGIC 4: TEXT TO SPEECH (TTS) - MOUTH
# ==========================================

def generate_voice(text: str):
    """Generates MP3 audio bytes using ElevenLabs Turbo."""
    if not text:
        return None
    try:
        # Returns a generator of bytes
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=TTS_MODEL,
            output_format="mp3_44100_128" # High quality MP3
        )
        
        # Consume the generator to get full bytes
        audio_bytes = b"".join(audio_generator)
        return audio_bytes

    except Exception as e:
        print(f"TTS Error: {e}")
        return None