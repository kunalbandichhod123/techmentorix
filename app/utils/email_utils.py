import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def send_otp(email, otp):
    msg = EmailMessage()
    msg.set_content(f"Your AyurMeal OTP is: {otp}")
    msg["Subject"] = "AyurMeal Login OTP"
    msg["From"] = os.getenv("SMTP_EMAIL")
    msg["To"] = email

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(os.getenv("SMTP_EMAIL"), os.getenv("SMTP_PASSWORD"))
    server.send_message(msg)
    server.quit()
