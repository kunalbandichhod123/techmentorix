import streamlit as st
import time
from query_engine import generate_answer
# import voice_engine as ve
from streamlit_mic_recorder import mic_recorder

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VedaBuddy - Ayurveda Assistant",
    page_icon="🌿",
    layout="wide" 
)

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main { background-color: #fdfcf0; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .st-emotion-cache-1c7n2ka { background-color: #e8f5e9; }
    
    /* Voice Mode UI Improvements */
    .voice-status {
        text-align: center;
        padding: 20px;
        border-radius: 20px;
        background: white;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Namaste! I am Vaidya. How can I help you balance your Doshas or improve your wellbeing today?"}
    ]

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "chat"

if "voice_greeted" not in st.session_state:
    st.session_state.voice_greeted = False

if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2913/2913520.png", width=100)
    st.title("VedaBuddy Settings")
    
    # Mode Toggle Logic
    if st.session_state.app_mode == "chat":
        if st.button("🎙️ Switch to Voice Assistant", use_container_width=True):
            st.session_state.app_mode = "voice"
            st.rerun()
    else:
        if st.button("💬 Return to Main Chat", use_container_width=True):
            st.session_state.app_mode = "chat"
            st.session_state.voice_greeted = False # Reset for next entry
            st.rerun()

    st.divider()
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()
    
    st.caption("Disclaimer: This tool provides information based on Vedic texts and is not a substitute for professional medical advice.")

# --- HELPER: TEXT ANIMATION ---
def typing_effect(text, container):
    full_text = ""
    for char in text:
        full_text += char
        container.markdown(f"### *{full_text}*")
        time.sleep(0.04)

# ==========================================
#  MODE 1: CHAT INTERFACE
# ==========================================
if st.session_state.app_mode == "chat":
    st.title("🌿 VedaBuddy Chat")
    st.markdown("##### *Detailed Ayurvedic Wisdom*")

    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about Doshas, Diet, or Herbs..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Consulting Vedic texts..."):
                response = generate_answer(prompt, session_id="streamlit_user")
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

# ==========================================
#  MODE 2: VOICE ASSISTANT INTERFACE
# ==========================================
else:
    st.title("🎙️ VedaBuddy Voice Mode")
    
    # 1. Automatic Greeting Logic (Only on first entry)
    if not st.session_state.voice_greeted:
        if st.button("🏮 Click to Start Consultation"):
            with st.spinner("VedaBuddy is waking up..."):
                greeting_text = ve.get_llm_greeting()
                audio_bytes = ve.generate_voice(greeting_text)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    st.session_state.voice_greeted = True
                    time.sleep(2)
                    st.rerun()

    # 2. Main Voice Interaction Loop
    if st.session_state.voice_greeted:
        status_placeholder = st.empty()
        live_question_placeholder = st.empty()
        
        status_placeholder.markdown("""<div class='voice-status'>🌿 Vaidya is listening... Speak when you are ready.</div>""", unsafe_allow_html=True)
        
        # JUST_ONCE=True allows the browser silence detection to trigger the stop automatically
        audio_data = mic_recorder(
            start_prompt="Listening... (Silent when finished)",
            stop_prompt="Processing your wisdom...",
            key="continuous_mic_loop",
            just_once=True,
            use_container_width=True
        )

        # 3. Handle Voice Question
        if audio_data and audio_data['id'] != st.session_state.last_processed_audio:
            st.session_state.last_processed_audio = audio_data['id']
            status_placeholder.empty()
            
            # A. Transcribe (Ears)
            user_text = ve.transcribe_audio(audio_data['bytes'])
            
            if user_text:
                # B. ANIMATE THE QUESTION ONLY (Instant visual feedback)
                typing_effect(f"You asked: {user_text}", live_question_placeholder)
                
                # C. Get Detailed Answer (Brain - Background Processing)
                # This ensures the detailed text is in the chat history
                full_detailed_answer = generate_answer(user_text, session_id="streamlit_user")
                st.session_state.messages.append({"role": "user", "content": user_text})
                st.session_state.messages.append({"role": "assistant", "content": full_detailed_answer})

                # D. Get Concise Script (No tags will be shown/heard)
                voice_script = ve.make_answer_listenable(full_detailed_answer)

                # E. Generate Audio & Play (Mouth)
                audio_response = ve.generate_voice(voice_script)
                
                if audio_response:
                    st.audio(audio_response, format="audio/mp3", autoplay=True)
                    
                    # F. INFINITE LOOP: Calculate wait time based on speech length then rerun
                    word_count = len(voice_script.split())
                    wait_time = word_count * 0.45  # Roughly 0.45s per word
                    time.sleep(max(3, wait_time)) 
                    
                    st.rerun() # Restarts the mic for the next question automatically
            else:
                st.warning("I couldn't hear you clearly. Let's try again.")
                time.sleep(1)
                st.rerun()

    # 4. History Management (Limit growth)
    if len(st.session_state.messages) > 30:
        st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-20:]