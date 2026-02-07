import React, { useState, useEffect, useRef } from 'react';
import './VoiceOverlay.css';
import CloseButton from '../CloseButton/CloseButton';
import PulseSphere from '../../animations/PulseSphere/PulseSphere';
import VoiceHeader from '../VoiceHeader/VoiceHeader';
import { TextAnimate } from '../../magicui/TextAnimate';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
// Import the new Button Component
import ControlToggle from '../ControlToggle/ControlToggle';

// 1. ACCEPT 'sessionId' PROP HERE
const VoiceOverlay = ({ onClose, onConversationUpdate, sessionId }) => {
  // --- STATE ---
  // 1. Transcript: Cyan Text (ONLY for User Input & Errors)
  const [transcript, setTranscript] = useState(""); 
  
  // 2. AI State: Upper Text (Status: Listening, Thinking, etc.)
  const [aiState, setAiState] = useState("initializing..."); 
  
  // Master Switch: Is the loop allowed to run?
  const [isConversationActive, setIsConversationActive] = useState(true);
  
  // Refs for tracking across re-renders/timeouts
  const audioRef = useRef(new Audio());
  const isActiveRef = useRef(true); 

  const { startRecording, stopRecording } = useVoiceRecorder();

  // --- 1. ENTRY POINT: GREETING ---
  useEffect(() => {
    // Start fresh
    isActiveRef.current = true;
    setIsConversationActive(true);
    
    const playGreeting = async () => {
      try {
        // STATUS UPDATE: Show in Upper Text
        setAiState("greeting...");
        // TRANSCRIPT UPDATE: Keep Cyan Text Empty
        setTranscript(""); 

        // Fetch Greeting Logic (Backend handles Day/Time dynamics)
        const response = await fetch("http://127.0.0.1:8000/greeting");
        const data = await response.json();

        if (data.audio) {
          audioRef.current.src = data.audio;
          audioRef.current.play();
          
          // STATUS UPDATE: Show "Saying Hello" in Upper Text
          setAiState("saying hello...");
          
          // When greeting ends -> Start the Main Loop
          audioRef.current.onended = () => {
             startConversationCycle();
          };
        } else {
          // Fallback if no audio
          startConversationCycle();
        }
      } catch (e) {
        console.error("Greeting failed", e);
        startConversationCycle();
      }
    };

    playGreeting();

    // CLEANUP
    return () => {
      isActiveRef.current = false;
      audioRef.current.pause();
      audioRef.current.src = "";
    };
  }, []);

  // --- 2. THE LOOP (RECURSIVE) ---
  const startConversationCycle = async () => {
    // STOP CHECK: If user pressed Stop, do NOT record.
    if (!isActiveRef.current) {
        setAiState("idle");
        // Keep the last transcript visible or clear it? 
        // Usually clearer to show "Paused" or keep last text.
        // Let's keep the last user text visible if it exists.
        return;
    }

    // A. Start Listening
    await startRecording();
    
    // STATUS UPDATE: Upper Text
    setAiState("listening...");
    // TRANSCRIPT UPDATE: Clear Cyan Text (Ready for new input)
    setTranscript(""); 

    // B. Wait 5s then Process
    setTimeout(async () => {
      if (isActiveRef.current) await processAudio();
    }, 5000);
  };

  // --- 3. PROCESS AUDIO (NEW SPLIT LOGIC) ---
  const processAudio = async () => {
    // STATUS UPDATE: Upper Text
    setAiState("thinking...");
    // Transcript stays empty while thinking

    const audioBlob = await stopRecording();
    
    // Safety check
    if (!isActiveRef.current) return;

    if (!audioBlob) {
        // Retry logic
        setTimeout(startConversationCycle, 1000);
        return;
    }

    // --- STEP A: INSTANT TRANSCRIPTION (The Fix) ---
    const formData = new FormData();
    formData.append("file", audioBlob, "input.wav");

    try {
      // 1. Call the Fast Transcribe Endpoint
      const transcribeResponse = await fetch("http://127.0.0.1:8000/transcribe", {
        method: "POST",
        body: formData,
      });
      const transcribeData = await transcribeResponse.json();

      if (!isActiveRef.current) return;

      if (transcribeData.error) {
        setTranscript("I didn't catch that.");
        setTimeout(startConversationCycle, 1500);
        return;
      }

      // 2. SHOW TEXT IMMEDIATELY (Animation Starts Here!)
      // This happens while the AI is still thinking about the answer.
      const userText = transcribeData.transcript;
      setTranscript(userText);
      setAiState("thinking..."); // Keep thinking state while fetching answer

      // --- STEP B: GET AI ANSWER (The Slow Part) ---
      const chatResponse = await fetch("http://127.0.0.1:8000/chat-voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            text: userText, 
            session_id: sessionId  // Send Random Session ID
        }),
      });
      const chatData = await chatResponse.json();

      if (!isActiveRef.current) return;

      // 3. UPDATE STATUS & SYNC CHAT
      setAiState("speaking...");

      // Bridge Logic: Sync with Main Chat History
      if (onConversationUpdate) {
         onConversationUpdate(userText, chatData.chat_answer);
      }

      if (chatData.audio) {
        audioRef.current.src = chatData.audio;
        audioRef.current.play();
        
        // RESTART LOOP when finished speaking
        audioRef.current.onended = () => {
           setTimeout(startConversationCycle, 500);
        };
      } else {
        setTimeout(startConversationCycle, 1000);
      }

    } catch (error) {
      console.error(error);
      if (isActiveRef.current) {
          // Connection Error - Show in Cyan
          setTranscript("Connection Error.");
          setTimeout(startConversationCycle, 3000);
      }
    }
  };

  // --- 4. TOGGLE HANDLER ---
  const handleToggle = () => {
    if (isConversationActive) {
      // STOP LOGIC
      setIsConversationActive(false);
      isActiveRef.current = false;
      
      // Kill current activities
      stopRecording(); 
      audioRef.current.pause();
      
      setAiState("idle");
      // Optional: Update transcript to show paused state?
      // setTranscript("Conversation Paused"); 
    } else {
      // START LOGIC
      setIsConversationActive(true);
      isActiveRef.current = true;
      startConversationCycle();
    }
  };

  return (
    <div className="voice-overlay-container relative w-full h-full">
      
      {/* 1. HEADER */}
      <div className="absolute top-8 left-0 w-full flex justify-center z-50">
        <VoiceHeader />
      </div>

      {/* 2. EXIT BUTTON (Top Left) */}
      <CloseButton onClose={onClose} />

      {/* 3. MAIN CONTENT CENTER */}
      <div className="flex flex-col items-center justify-center pb-10 w-full h-full">
        
        {/* SPHERE */}
        <PulseSphere state={aiState} />
        
        {/* STATUS TEXT (Upper Text - White/Gray) 
            - Shows: LISTENING..., THINKING..., SPEAKING..., SAYING HELLO...
        */}
        <h2 className="text-white/40 text-[20px] font-light tracking-[0.3em] animate-pulse mt-[-10px] mb-12 uppercase">
          {aiState === "idle" ? "PAUSED" : aiState}
        </h2>

        {/* USER TRANSCRIPT (Lower Text - Cyan Blue) 
            - Shows: User's Question (e.g. "What is Vata?") or Error Messages
        */}
        <div className="h-16 w-full max-w-3xl flex items-start justify-center px-6">
          <TextAnimate
            key={transcript} 
            animation="slideUp"
            by="word"
            className="text-cyan-400 text-[28px] font-light tracking-wide text-center drop-shadow-[0_0_15px_rgba(34,211,238,0.3)]"
          >
            {transcript}
          </TextAnimate>
        </div>

      </div>

      {/* 4. CONTROL BUTTON (Positioned Absolute Right) */}
      <div className="absolute bottom-10 right-10 z-50">
        <ControlToggle 
          isActive={isConversationActive} 
          onToggle={handleToggle} 
        />
      </div>

    </div>
  );
};

export default VoiceOverlay;