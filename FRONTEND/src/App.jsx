import { useState, useEffect } from 'react';
import BackgroundVideo from './components/layout/BackgroundVideo';
import ChatInput from './components/chat/ChatInput';
import ChatMessages from './components/chat/ChatMessages';
import Header from './components/layout/Header';
import VoiceOverlay from './components/voice/VoiceOverlay/VoiceOverlay';
import { usePorcupine } from '@picovoice/porcupine-react';

function App() {
  const [userInput, setUserInput] = useState("");
  const [isTyping, setIsTyping] = useState(false); // New state for loading
  
  // 2. New State for Voice Mode Switch
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  
  // 3. GENERATE UNIQUE SESSION ID (ON PAGE LOAD)
  // This creates a random string (e.g., "session_a1b2c3") every time the page refreshes.
  // This ensures every visitor gets a fresh "Brain" history.
  const [sessionId] = useState(() => "session_" + Math.random().toString(36).substring(7));

  const [messages, setMessages] = useState([
    { role: "ai", content: "Welcome, seeker. How can I guide your Ayurvedic journey today?" }
  ]);

  // --- START NEW LOGIC: WAKE WORD ENGINE ---
  // We use the 'init' method to manually load both the Wake Word (.ppn) and the Model (.pv)
  // This fixes the "Initializing..." freeze issue.
  const {
    keywordDetection,
    isLoaded,
    isListening,
    error,
    init,
    start,
    stop,
  } = usePorcupine();

  // LOGIC A: INITIALIZE ENGINE (Runs once on mount)
  useEffect(() => {
    const initEngine = async () => {
      try {
        await init(
          import.meta.env.VITE_PICOVOICE_ACCESS_KEY,
          // 1. The Wake Word File
          { publicPath: "/models/hey_karuna.ppn", label: "Hey Karuna" },
          // 2. The Model File (Crucial fix)
          { publicPath: "/models/porcupine_params.pv" }
        );
        console.log("✅ Wake Word Engine Loaded Successfully");
      } catch (err) {
        console.error("❌ Failed to load Wake Word:", err);
      }
    };
    initEngine();
  }, []); // Empty dependency array = runs once

  // LOGIC B: DETECT WAKE WORD
  useEffect(() => {
    if (keywordDetection !== null) {
      console.log("✨ Wake Word Detected: Hey Karuna");
      setIsVoiceMode(true); // Triggers the switch to Voice Mode
    }
  }, [keywordDetection]);

  // LOGIC C: MIC HANDOFF (CRITICAL)
  // This ensures 'Hey Karuna' and 'Voice Mode' never fight for the mic.
  useEffect(() => {
    if (!isLoaded) return; // Wait until engine is ready

    const manageMic = async () => {
      if (isVoiceMode) {
        // 1. Voice Mode is OPEN -> STOP listening for Wake Word
        if (isListening) {
          console.log("🛑 Pausing Wake Word (Voice Mode Active)");
          await stop();
        }
      } else {
        // 2. Voice Mode is CLOSED -> START listening for Wake Word
        if (!isListening) {
          console.log("👂 Starting Wake Word Listener...");
          try {
            await start();
          } catch (e) {
            console.error("Wake word failed to start:", e);
          }
        }
      }
    };
    manageMic();
  }, [isVoiceMode, isLoaded, isListening, start, stop]);
  // --- END NEW LOGIC ---

  // UPDATED: Now an async function to call the Real Backend
  const handleSend = async () => {
    if (!userInput.trim()) return;
    
    // 1. Capture user message
    const currentText = userInput; // Store locally to send in API
    const userMessage = { role: "user", content: currentText };
    
    // 2. Update state with user message immediately
    setMessages((prev) => [...prev, userMessage]);
    
    // 3. Clear the input
    setUserInput("");

    // 4. Start Loading Animation
    setIsTyping(true);

    try {
      // 5. REAL BACKEND CALL
      // We send the text to the Python /chat endpoint
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // Matches the 'ChatRequest' model in your main.py
        body: JSON.stringify({ 
          question: currentText,
          // SEND DYNAMIC SESSION ID (Instead of fixed 'web_user_1')
          session_id: sessionId 
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to connect to VedaBuddy Backend");
      }

      const data = await response.json();

      // 6. Stop Loading & Show Real Answer
      setIsTyping(false);

      const aiResponse = { 
        role: "ai", 
        content: data.answer // 'answer' comes from main.py return {"answer": ...}
      };
      setMessages((prev) => [...prev, aiResponse]);

    } catch (error) {
      console.error("Chat Error:", error);
      setIsTyping(false);
      
      // Fallback error message for UI
      const errorMsg = { 
        role: "ai", 
        content: "I apologize, but I cannot reach the ancient texts right now. Please check if the Python backend is running." 
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  // --- NEW: BRIDGE FUNCTION FOR VOICE ---
  // This receives the User's Spoken Text and the AI's Full Detailed Answer
  // and adds them to the main chat history.
  const handleVoiceConversation = (userTranscript, aiDetailedAnswer) => {
    // 1. Add User's Spoken Question
    const userMsg = { role: "user", content: userTranscript };
    
    // 2. Add AI's Detailed RAG Answer (Not the short voice script)
    const aiMsg = { role: "ai", content: aiDetailedAnswer };

    // Update the main history
    setMessages((prev) => [...prev, userMsg, aiMsg]);
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black text-white flex flex-col items-center">
      
      {/* 1. MOTION BACKGROUND (Always Visible) */}
      <BackgroundVideo src="/main-bg.mp4" />

      {/* 2. TOP HEADER (Always Visible) */}
      <Header />

      {/* 3. CONDITIONAL RENDER: Voice Mode vs Text Chat */}
      {isVoiceMode ? (
        
        /* --- VOICE MODE INTERFACE --- */
        <div className="relative z-50 flex-1 w-full pt-24">
              {/* Pass sessionId down so Voice Mode uses the same brain history */}
              <VoiceOverlay 
                onClose={() => setIsVoiceMode(false)} 
                onConversationUpdate={handleVoiceConversation}
                sessionId={sessionId}
              />
        </div>

      ) : (

        /* --- STANDARD TEXT CHAT INTERFACE --- */
        <>
          {/* CENTER STAGE & CHAT FEED */}
          {/* Changed pt-16 to pt-24 so messages start below the header */}
          <div className="relative z-20 flex-1 w-full flex flex-col items-center justify-start pt-24 overflow-hidden">
            
            {/* Particle Sphere Placeholder (Optional background glow) */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none -z-10">
               <div className="w-64 h-64 rounded-full bg-cyan-500/5 blur-3xl animate-pulse" />
            </div>

            {/* Updated with messages and isTyping state */}
            <ChatMessages messages={messages} isTyping={isTyping} />
          </div>

          {/* INPUT UI */}
          <div className="relative z-30 w-full flex flex-col items-center p-6 md:p-12 pb-10">
            <ChatInput 
              value={userInput} 
              onChange={setUserInput} 
              onSend={handleSend} 
              /* This triggers the switch to Voice Mode */
              onMicClick={() => setIsVoiceMode(true)}
            />
          </div>
        </>
      )}
      
    </div>
  );
}

export default App;