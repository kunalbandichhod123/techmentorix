# test_openai_key.py
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENAI_API_KEY")
if not key:
    print("OPENAI_API_KEY missing in .env")
    raise SystemExit(1)

client = OpenAI(api_key=key)

try:
    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":"Say hello in one line"}],
        max_tokens=10
    )
    print("OK — model responded:", res.choices[0].message.content.strip())
except Exception as e:
    print("ERROR:", type(e), e)
    # Print full debug so you can copy into support ticket
    import traceback; traceback.print_exc()
