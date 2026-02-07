import time
import pandas as pd
import matplotlib.pyplot as plt
import os
from groq import Groq
from dotenv import load_dotenv

# Import your actual RAG brain
from query_engine import generate_answer

# Setup
load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- 1. THE GOLDEN DATASET (Shortened to safe limits) ---
TEST_QUESTIONS = [
    "I have vata tell me good breakfast options",
    "I have pitta guide me some yoga",
    "Suggest me some soups for my high pitta",
    "Tell me about the bhujangasana",
    "Foods to avoid for high pitta person",
    "Simple kadha recipe for my pitta"
]

# --- 2. THE JUDGE (LLM) ---
def evaluate_answer(question, answer):
    """Uses LLM to grade the answer."""
    judge_prompt = (
        f"You are an impartial judge evaluating an AI Medical Assistant.\n"
        f"QUESTION: {question}\n"
        f"AI ANSWER: {answer}\n"
        f"Task: Rate the AI Answer on two metrics (0-10 scale):\n"
        f"1. RELEVANCE: Does it directly answer the user's question?\n"
        f"2. CLARITY: Is the advice easy to understand?\n"
        f"OUTPUT FORMAT (Strict JSON): {{'relevance': 9, 'clarity': 8}}"
    )
    
    try:
        # SLEEP 1: Pause before calling Judge to prevent 429 Error
        time.sleep(2) 
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return eval(completion.choices[0].message.content)
    except Exception as e:
        print(f"  [Judge Error]: {e}")
        return {'relevance': 5, 'clarity': 5} # Neutral score on error

# --- 3. THE EXPERIMENT LOOP ---
results = []

print("Starting Model Evaluation (Safe Mode)...")

for i, q in enumerate(TEST_QUESTIONS):
    print(f"\n[{i+1}/{len(TEST_QUESTIONS)}] Asking: {q}...")
    
    try:
        # Measure Latency
        start_time = time.time()
        response = generate_answer(q, session_id="eval_test_user") 
        end_time = time.time()
        latency = round(end_time - start_time, 2)
        
        # Measure Quality
        scores = evaluate_answer(q, response)
        
        # Print Result Live
        print(f"  -> Latency: {latency}s | Relevance: {scores['relevance']}/10")

        results.append({
            "Question": q,
            "Latency (s)": latency,
            "Relevance Score": scores['relevance'],
            "Clarity Score": scores['clarity']
        })
        
        # SLEEP 2: Crucial Pause between questions
        print("  -> Cooling down for 5 seconds...")
        time.sleep(6) 

    except Exception as e:
        print(f"  [Error on Q{i+1}]: {e}")
        # Continue to next question instead of crashing
        continue

# --- 4. GENERATE REPORT ---
if not results:
    print("No results collected. Check API Key or Connection.")
    exit()

df = pd.DataFrame(results)

# Save to CSV
csv_filename = "vedabuddy_performance_report.csv"
df.to_csv(csv_filename, index=False)
print(f"\n[SUCCESS] Saved data to '{csv_filename}'")

# --- 5. GENERATE GRAPHS ---
try:
    # Graph 1: Latency
    plt.figure(figsize=(10, 5))
    plt.bar(df.index + 1, df["Latency (s)"], color='#4CAF50')
    plt.title("VedaBuddy Response Latency")
    plt.xlabel("Question #")
    plt.ylabel("Seconds")
    plt.savefig("graph_latency.png")
    print("[SUCCESS] Generated 'graph_latency.png'")

    # Graph 2: Quality
    plt.figure(figsize=(10, 5))
    plt.plot(df.index + 1, df["Relevance Score"], marker='o', label="Relevance", color='blue')
    plt.plot(df.index + 1, df["Clarity Score"], marker='s', label="Clarity", color='orange')
    plt.title("VedaBuddy Quality Scores")
    plt.ylim(0, 11)
    plt.xlabel("Question #")
    plt.ylabel("Score (0-10)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("graph_quality.png")
    print("[SUCCESS] Generated 'graph_quality.png'")

except Exception as e:
    print(f"Graph Error: {e}")
    print("Don't worry, your CSV is safe! You can make graphs in Excel if needed.")