# pylint: disable=import-error
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

# Using the exact variable name from your .env
SENDGRID_API_KEY = os.getenv("sendgrid_api_key")
# Using the verified sender email from your .env
FROM_EMAIL = os.getenv("SMTP_EMAIL", "shejoleneha@gmail.com")

def send_email_otp(to_email: str, otp: str):
    """
    Sends a 6-digit OTP to the specified email address using SendGrid.
    """
    if not SENDGRID_API_KEY:
        print("❌ ERROR: sendgrid_api_key not found in .env")
        return False

    subject = "Your AyurMeal Password Reset OTP"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; color: #333;">
        <h2>Password Reset Request</h2>
        <p>Hello,</p>
        <p>You requested to reset your password. Use the OTP below to proceed:</p>
        <h1 style="color: #2E7D32; letter-spacing: 5px;">{otp}</h1>
        <p>This OTP is valid for 10 minutes.</p>9+
        <p>If you did not request this, please ignore this email.</p>
    </div>
    """

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} | Status Code: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False