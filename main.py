import os
import json
import random
import csv
import requests  # Added for Resend API
from fastapi import FastAPI
from pydantic import BaseModel
from google.oauth2 import service_account
from google import genai  # Updated Gemini import
# Updated Gemini client initialization
# (This automatically reads the GEMINI_API_KEY from your environment variables)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Suyog Plus backend is running"}

OTP_STORE = {}
USER_SESSIONS = {} 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ChatPayload(BaseModel):
    user_message: str
    email: str
    current_step: str

def send_real_email(target_email: str, otp_code: str):
    try:
        resend_api_key = os.getenv("RESEND_API_KEY")
        
        # Send via normal HTTP web traffic which Railway allows
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "onboarding@resend.dev",  # Resend provides this domain for free testing
            "to": target_email,
            "subject": "Your Suyog+ Verification Code",
            "html": f"<p>Your verification code is: <strong>{otp_code}</strong></p>"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"EMAIL ERROR: {response.text}")
            return False
            
    except Exception as e:
        print(f"EMAIL ERROR: {e}")
        return False

# ... (You can keep your existing find_top_jobs function here) ...

@app.post("/api/chat")
def chat_endpoint(payload: ChatPayload):
    msg_orig = payload.user_message.strip()
    email = payload.email.strip().lower()
    step = payload.current_step

    if step == "get_email":
        otp = str(random.randint(1000, 9999))
        OTP_STORE[email] = otp
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
            # Updated to use the new client syntax and recommended gemini-2.5-flash model
            prompt = f"Extract Name and Department from: '{msg_orig}'. Reply exactly: NAME: [name] | DEPT: [department]"
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
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

    # ... (Keep the rest of your qualification steps here) ...
