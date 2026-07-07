import os
import json
import smtplib
import random
from email.mime.text import MIMEText
from fastapi import FastAPI
from pydantic import BaseModel
import csv
from google.oauth2 import service_account
import google.generativeai as genai

# You would typically download a JSON key file from your Google Cloud Console
# and set the path in your Railway environment variables as GOOGLE_APPLICATION_CREDENTIALS
# This is the industry-standard way to use those secure AQ/Auth keys.

# Setup Gemini & Email from Railway Environment Variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()
OTP_STORE = {}
USER_SESSIONS = {} 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ChatPayload(BaseModel):
    user_message: str
    email: str
    current_step: str

def send_real_email(target_email: str, otp_code: str):
    try:
        msg = MIMEText(f"Your verification code is: {otp_code}")
        msg["Subject"] = "Your Suyog+ Verification Code"
        msg["From"] = os.getenv("GMAIL_USER")
        msg["To"] = target_email
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
            server.sendmail(os.getenv("GMAIL_USER"), target_email, msg.as_string())
        return True
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        return False

# ... (Keep your existing find_top_jobs function here) ...

@app.post("/api/chat")
def chat_endpoint(payload: ChatPayload):
    msg_orig = payload.user_message.strip()
    email = payload.email.strip().lower()
    step = payload.current_step

    if step == "get_email":
        otp = str(random.randint(1000, 9999))
        OTP_STORE[email] = otp
        # Now calling the real email function
        success = send_real_email(email, otp)
        if success:
            return {"status": "success", "ai_response": "Code sent! Check your email.", "next_step": "verify_code"}
        else:
            return {"status": "error", "ai_response": "Email failed. Check logs.", "next_step": "get_email"}

    elif step == "verify_code":
        if OTP_STORE.get(email) == msg_orig.lower():
            del OTP_STORE[email]
            return {"status": "success", "ai_response": "Login success! Introduce yourself (Name & Dept).", "next_step": "get_intro"}
        return {"status": "error", "ai_response": "Wrong code.", "next_step": "verify_code"}

    elif step == "get_intro":
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Extract Name and Department from: '{msg_orig}'. Reply exactly: NAME: [name] | DEPT: [department]"
            response = model.generate_content(prompt)
            reply = response.text.strip()
            
            name, dept = "User", "Unknown"
            if "NAME:" in reply and "|" in reply:
                parts = reply.split("|")
                name = parts[0].replace("NAME:", "").strip()
                dept = parts[1].replace("DEPT:", "").strip()
            
            USER_SESSIONS[email] = {"Email": email, "Name": name, "Department": dept}
            return {"status": "success", "ai_response": f"Hi {name}! Interest in {dept} noted. Qualification?", "next_step": "get_qualification"}
        except Exception as e:
            return {"status": "error", "ai_response": f"Error: {str(e)}", "next_step": "get_intro"}

    # ... (Keep the rest of your qualification/disability/functional logic) ...
