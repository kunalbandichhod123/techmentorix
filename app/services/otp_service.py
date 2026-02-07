# app/services/otp_service.py
import os
import random
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client

# ---------------- 1. FORCE LOAD .ENV ----------------
# This logic finds the .env file 3 folders up (in the root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# ---------------- 2. GET VARIABLES (THE FIX) ----------------
# 👇 We changed these to match your .env file exactly!
SID = os.getenv("ACCOUNT_SID")       # Matches .env
TOKEN = os.getenv("AUTH_TOKEN")      # Matches .env
PHONE_NUMBER = os.getenv("TWILIO_NUMBER") # Matches .env

# ---------------- 3. DEBUG PRINT ----------------
# This prints to the terminal so you can verify it loaded
print(f"DEBUG: Loaded SID: {SID[:5] if SID else 'None'}")
print(f"DEBUG: Loaded Token: {TOKEN[:3] if TOKEN else 'None'}")

otp_store = {}

def send_otp(phone: str):
    # 1. Generate OTP
    otp = str(random.randint(100000, 999999))
    otp_store[phone] = otp

    # 2. ALWAYS PRINT TO CONSOLE (Your Backup)
    print(f"========================================")
    print(f"🔐 SIMULATED OTP FOR {phone}: {otp}")
    print(f"========================================")

    # 3. Try Sending via Twilio
    try:
        # Check if keys are missing BEFORE trying to connect
        if not SID or not TOKEN or not PHONE_NUMBER:
            print("⚠️ Twilio credentials missing in .env (Using Console OTP)")
            return {"message": "OTP generated (Console Only)"}

        client = Client(SID, TOKEN)
        client.messages.create(
            body=f"Your AyurMeal OTP is {otp}",
            from_=PHONE_NUMBER,
            to=phone
        )
        print(f"✅ Twilio SMS sent to {phone}")
        
    except Exception as e:
        # Catch error so app doesn't crash
        print(f"⚠️ Twilio Failed: {e}") 
        print("➡️ Use the 6-digit code printed above to login.")

    return {"message": "OTP processed"}

def verify_otp(phone: str, otp: str):
    """Check if OTP matches for given phone"""
    stored_otp = otp_store.get(phone)
    if stored_otp and str(stored_otp) == str(otp):
        del otp_store[phone]  # Remove after success
        return True
    return False