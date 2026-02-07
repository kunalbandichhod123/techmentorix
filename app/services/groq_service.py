import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# app/services/groq_service.py

# ... keep existing imports ...

def generate_meal_plan(patient: dict) -> str:
    prompt = f"""
   You are an Ayurvedic dietitian. Output EXACTLY valid JSON ONLY (no text outside JSON).
Generate a 7-day plan labeled "Day 1" ... "Day 7". Generate a 7-day Ayurvedic meal plan in strict JSON format. For each meal, provide exactly two food options with calories. each day should be a new indian recipe do not repeate recipes in a 2 or 3 days.Always provide Indian foods and also include a "Recipes" list per day with name, ingredients, and instructions (e.g., Kadha, Haldi milk ) dont add directly from breakfast,it should be ayurvedic recipes which are hard to make by patients. Each day must be an object:
    
    JSON STRUCTURE (STRICT):
    {{
      "Day 1": {{
        "meals": [
          {{ "meal": "Breakfast", "opt1": "...", "cal1": "250", "opt2": "...", "cal2": "100" }},
          {{ "meal": "Snack", "opt1": "...", "cal1": "120", "opt2": "...", "cal2": "100" }},
          {{ "meal": "Lunch", "opt1": "...", "cal1": "500", "opt2": "...", "cal2": "550" }},
          {{ "meal": "Dinner", "opt1": "...", "cal1": "600", "opt2": "...", "cal2": "450" }}
        ],
        "workout": ["Yoga", "Walking"],
        "lifestyle": "...",
        "recipe": {{ "name": "...", "ing": "...", "ins": "..." }}
      }},
      "Day 2": {{ ... }},
      ... up to Day 7
    }}
    """
    # ... keep the response_format={"type": "json_object"} call ...

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={ "type": "json_object" } # Strict JSON enforcement
    )

    # Return the raw JSON string directly to the DB
    return response.choices[0].message.content.strip()