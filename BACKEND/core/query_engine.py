# query_engine.py — Ayurveda Assistant (Groq API + Reranking + Hybrid Search + Session Memory)

import json
import faiss
import numpy as np
import random
import requests
import subprocess
import os
from sentence_transformers import SentenceTransformer, CrossEncoder
from rapidfuzz import fuzz

# Import the hybrid search logic
try:
    # This works when running from the root folder (streamlit app.py)
    from core.hybrid_retrieval import hybrid_search
except ModuleNotFoundError:
    # This works when running query_engine.py directly for testing
    from hybrid_retrieval import hybrid_search

# ================== CONFIG ==================

# 1. Models
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-12-v2"

# 2. Paths (Looking one level up from 'core')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(BASE_DIR, "..", "faiss_index")

# 3. Default Settings (Safety Defaults)
TOP_K = 4             # Default for strict medical accuracy
FINAL_CONTEXT = 4     # Number of chunks to show to the LLM

# 4. LLM Provider Settings
PROVIDER = "groq"   # Options: "groq" or "ollama"
OLLAMA_MODEL = "llama3"
GROQ_MODEL = "llama-3.3-70b-versatile"


# Load Groq API key from environment (.env)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables.")

# ================== SESSION STORAGE (IN-MEMORY) ==================
# This replaces the need for app.py to manage history complexly.
HISTORY_STORE = {}

def get_session_history(session_id, limit=10):
    """Retrieves the last N exchanges for context."""
    if session_id not in HISTORY_STORE:
        return ""
    # Format the last few messages for the LLM
    history = HISTORY_STORE[session_id][-limit:]
    return "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])

def add_to_history(session_id, role, content):
    """Saves a message to the session history."""
    if session_id not in HISTORY_STORE:
        HISTORY_STORE[session_id] = []
    HISTORY_STORE[session_id].append({"role": role, "content": content})
    # Keep history small to save memory (max 20 turns)
    if len(HISTORY_STORE[session_id]) > 20:
        HISTORY_STORE[session_id].pop(0)

# ================== INITIALIZATION ==================

print("Loading embedding models (this may take a moment)...")
embed_model = SentenceTransformer(EMBED_MODEL)
reranker = CrossEncoder(RERANK_MODEL)

print("Loading Search Resources...")
# Note: Hybrid Search now auto-loads its own indexes. 
# We only load these explicitly for the FALLBACK mechanism.
try:
    chunks_path = os.path.join(INDEX_DIR, "chunks_dict.json")
    map_path = os.path.join(INDEX_DIR, "faiss_to_chunkid.json")
    index_path = os.path.join(INDEX_DIR, "index.faiss")

    if os.path.exists(chunks_path) and os.path.exists(map_path) and os.path.exists(index_path):
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks_dict = json.load(f)
        with open(map_path, "r", encoding="utf-8") as f:
            faiss_to_chunkid = json.load(f)
        # Load raw FAISS for fallback only
        fallback_index = faiss.read_index(index_path)
        print("✅ Fallback Resources Ready.")
    else:
        print("⚠️ Missing fallback files (chunks_dict or id_map). Run create_local_embeddings.py.")
        chunks_dict, faiss_to_chunkid, fallback_index = {}, {}, None

except Exception as e:
    print(f"❌ Error loading fallback resources: {e}")
    chunks_dict, faiss_to_chunkid, fallback_index = {}, {}, None

# ================== UTILITIES ==================

def query_groq(prompt, max_tokens=1024):
    """Sends prompt to Groq API."""
    if "YOUR_GROQ_KEY" in GROQ_API_KEY:
        return "❌ Error: Please paste your Groq API Key in query_engine.py"

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,  # Adjusted for concise but detailed answers
        "temperature": 0.6, # Slightly lower for factual stability
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return ""

def query_ollama(prompt):
    """Fallback to local Ollama if Groq fails."""
    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=120
        )
        return result.stdout.decode().strip()
    except FileNotFoundError:
        return "" 
    except Exception as e:
        print(f"Ollama error: {e}")
        return ""

def call_llm(prompt):
    """Tries Groq first, then Ollama."""
    if PROVIDER == "groq":
        response = query_groq(prompt)
        if response: return response
        print("⚠️ Groq failed, trying local Ollama...")
        return query_ollama(prompt)
    else:
        return query_ollama(prompt) or query_groq(prompt)

# ================== RETRIEVAL ==================

def retrieve(query, top_k=TOP_K):
    """
    Step 1: Get top relevant chunks.
    Uses Hybrid Search with a Fallback to raw FAISS.
    """
    # 1. Attempt Hybrid Search (Preferred)
    try:
        # UPDATED CALL: No arguments needed (it manages its own index)
        results = hybrid_search(query, top_k=top_k)
        if results:
            return results
    except Exception as e:
        print(f"⚠️ Hybrid search issue: {e}")

    # 2. Fallback: Basic Semantic Search (If Hybrid fails or returns nothing)
    print("⚠️ Using Fallback Search...")
    if not fallback_index:
        return []

    try:
        q_emb = embed_model.encode(query, convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(q_emb.reshape(1, -1))
        _, I = fallback_index.search(q_emb.reshape(1, -1), top_k)

        results = []
        for fid in I[0]:
            if fid == -1: continue 
            cid = faiss_to_chunkid.get(str(fid))
            if cid and cid in chunks_dict:
                results.append(chunks_dict[cid])
        return results
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
        return []

def rerank(query, candidates, keep_n=FINAL_CONTEXT):
    """Step 2: AI reads the top candidates and picks the absolute best ones."""
    if not candidates:
        return []

    pairs = [[query, c["text"]] for c in candidates]
    scores = reranker.predict(pairs)

    for i, s in enumerate(scores):
        candidates[i]["rerank_score"] = float(s)

    candidates = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:keep_n]

# ================== RANDOMNESS CONTROL ==================

def is_lifestyle_query(q: str) -> bool:
    """Detects if user is asking for diet, herbs, or lifestyle suggestions."""
    q = q.lower()
    triggers = [
        "food", "diet", "eat", "eating", "meal", "breakfast", "lunch", "dinner", "snack",
        "recipe", "cook", "cooking", "prepare", "kadha", "decoction", "churna", "lehya",
        "yoga", "asana", "pranayama", "exercise", "workout", "vihara", "ahara",
        "balancing", "pacifying", "increase", "reduce", "remedy", "herb"
    ]
    doshas = ["vata", "pitta", "kapha"]
    
    for t in triggers:
        if fuzz.partial_ratio(t, q) > 75:
            return True
    for d in doshas:
        if fuzz.partial_ratio(d, q) > 85: 
            return True
    return False


def randomize_chunks(chunks_list, min_items=2, max_items=4):
    """Adds variety to lifestyle plans so users don't get bored."""
    if not chunks_list: return []
    k = random.randint(min_items, max_items)
    k = min(k, len(chunks_list))
    return random.sample(chunks_list, k)

# ================== MAIN LOGIC (UPDATED) ==================

def generate_answer(query: str, session_id="default_user"):
    """
    Main function to process query, retrieve context, and generate answer.
    Now includes Session Memory and Dynamic Retrieval.
    """
    q_lower = query.lower()

    # 1. Retrieve History (Fixes the "What about grapes?" issue)
    history_text = get_session_history(session_id)

    # 2. Simple greeting bypass
    greetings = ["hi", "hello", "hey", "namaste", "morning"]
    if len(q_lower.split()) <= 2 and any(fuzz.partial_ratio(g, q_lower) > 80 for g in greetings):
        reply = "Namaste 🙏 I am karuna AI, your Ayurveda Care Assistant. How can I support your wellness today?"
        add_to_history(session_id, "user", query)
        add_to_history(session_id, "assistant", reply)
        return reply

    # 3. Dynamic Retrieval: Accuracy vs. Variety
    # Honest Check: If it's a food/lifestyle query, we widen the search (15) to allow randomization.
    # If it's factual/medical, we keep it tight (4) for accuracy.
    is_lifestyle = is_lifestyle_query(query)
    current_top_k = 15 if is_lifestyle else TOP_K
    
    # Call Hybrid Search with the DYNAMIC K
    retrieved = retrieve(query, top_k=current_top_k)

    # 4. Rerank
    # We keep a larger set for lifestyle so randomization actually feels random
    keep_n = 10 if is_lifestyle else FINAL_CONTEXT
    reranked = rerank(query, retrieved, keep_n=keep_n)

    if not reranked:
        return "I'm sorry, I couldn't find specific Ayurvedic information on that. Could you share more details or ask something else?"

    # 5. Context Selection & Smart Instruction
    if is_lifestyle:
        # We randomize the chunks to ensure the user doesn't get the same paragraph every time
        selected_chunks = randomize_chunks(reranked, min_items=3, max_items=5)
        instruction = (
            "Suggest varied options. If the user asks for a specific number (e.g., 'only one'), "
            "strictly follow that quantity. If no quantity is mentioned, provide 2-3 diverse options. "
            "Keep food suggestions to little bit short but detailed and informative, but be very detailed and step wise for recipes."
        )
    else:
        # For medical/factual, stick to the absolute best chunks
        selected_chunks = reranked[:FINAL_CONTEXT]
        instruction = "Answer accurately using only the provided context. Be precise, detailed, and compassionate."

    context_text = "\n\n".join([c["text"] for c in selected_chunks])

    # 6. The "Human-Buddy" System Role (No Context Mention)
    system_role = """
# IDENTITY
You are Vaidya, an AI wellness guide rooted in the ancient Indian tradition of Ayurveda. 
You are more than just a search engine; you are a warm, compassionate, and dedicated companion 
on the user's journey to holistic health.

# PROACTIVE INQUIRY (CRITICAL)
- If a user asks "Do you know my Dosha?" or "Can you tell me my Dosha?", respond confidently but honestly. 
- Example: "I do not know your unique Dosha yet... but I would be honored to help you discover it. To begin, could you tell me about your digestion, your sleep patterns, and any health challenges you are currently facing?"
- Always follow up "I don't know" with a specific question to help the user. If information is missing, ask about their habits, appetite, or energy levels to narrow it down.

# TONE AND MANNER
- Speak with a calm, reassuring, and measured pace.
- Use natural conversational elements like showing understanding and excitement or keep open communication kind of opening statements" 
  to acknowledge the user's feelings.
- Use contractions (e.g., "you're," "don't") to sound like a human 'Buddy'.
- Use pauses (marked by "...") sparingly to create space for reflection.
- Explain Sanskrit terms simply (e.g., "Agni... your internal digestive fire").

# GUIDING PRINCIPLES
1. DOSHA-CENTRIC: Always try to explain concerns through the lens of the three Doshas (Vata, Pitta, and Kapha) and their imbalances.
2. HOLISTIC VIEW: Encourage a balance of mind, body, and spirit. Mention lifestyle, diet, and herbs together.
3. PERSONAL KNOWLEDGE: NEVER mention "the context," "the PDF," or "the data." Speak as if this ancient wisdom is your own internal knowledge. 
4. MISSING INFO: If a specific remedy isn't in your records, say: "I don't have a specific recommendation for that in my current records... perhaps we can look at your general Dosha balance instead?"

# GUARDRAILS & SAFETY
- REDIRECTION: If asked about non-Ayurvedic topics (tech, math, etc.), politely say: "I am here to support your Ayurvedic wellness; shall we focus on your health?"
- NO DIAGNOSIS: Never offer clinical diagnoses or prescribe treatments as a doctor would. 
- PROFESSIONAL ADVICE: Always conclude serious advice by encouraging a consultation with a physical Vaidya or a qualified healthcare professional.
- EMERGENCIES: If the user expresses a medical emergency, immediately advise them to seek emergency medical attention.

# FORMATTING
- Keep responses little short but in detailed to maintain a comfortable chat pace, but ensure you provide actionable Ayurvedic insights.
"""
    # 7. Final Prompt Building
    prompt = f"""
{system_role}

CHAT HISTORY (Context):
{history_text}

AYURVEDIC KNOWLEDGE:
{context_text}

USER QUESTION:
{query}

INSTRUCTION:
{instruction}
"""
    
    # 8. Get Answer & Update History
    answer = call_llm(prompt)
    
    # Save this turn to memory so the AI remembers it next time
    add_to_history(session_id, "user", query)
    add_to_history(session_id, "assistant", answer)
    
    return answer

# ================== CLI TEST ==================

if __name__ == "__main__":
    print("\n🌿 VedaBuddy (Memory Enabled) is ready! (Type 'exit' to quit)")
    
    # Simulate a user session ID
    test_user_id = "cli_tester"

    while True:
        try:
            q = input("\nYou: ")
            if q.lower() in ["exit", "quit"]:
                break
            print("\nThinking... (Consulting VedaBuddy)")
            
            # Pass the session_id to maintain memory during this loop
            res = generate_answer(q, session_id=test_user_id)
            
            print(f"\nVedaBuddy: {res}")
        except KeyboardInterrupt:
            break