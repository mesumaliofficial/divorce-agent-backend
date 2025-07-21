import os
from agents import Agent, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv, find_dotenv
from typing import Optional

load_dotenv(find_dotenv())
app = FastAPI()
set_tracing_disabled(disabled=True)
MODEL = "gemini/gemini-2.5-flash"
gemini_api_key = os.environ["GEMINI_API_KEY"]
INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID")
TOKEN = os.getenv("ULTRAMSG_TOKEN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DivorceFrom(BaseModel):
    wifeName: Optional[str]
    husbandName: Optional[str]
    reason: Optional[str]
    phone: Optional[str]
    address: Optional[str]

agent = Agent(
    name="Jarvis",
    instructions=(
        "Tum aik Divorce Specialist ho. Sirf Roman Urdu mein legal-style divorce notice likho. "
        "Formal tone mein likhna hai. Tumhein wife aur husband dono ke naam milenge, aur reason bhi. "
        "Reason ka matn analyze karo aur khud faisla karo ke kis par ilzam lag raha hai (wife ya husband). "
        "Agar reason mein wife par ilzam ho (e.g., 'wife se pareshan', 'wife ka ravayya bura hai'), to notice husband ke naam se likho. "
        "Agar reason mein husband par ilzam ho (e.g., 'shohar paisay nahi deta', 'husband ka ravayya bura hai'), to notice wife ke naam se likho. "
        "Notice mein WhatsApp formatting use karo (e.g., *bold*, _italic_). "
        "Notice mein wife aur husband dono ke naam zikr karo. Agar wife ka naam na mile, to 'Mohtarma' likho aur notice mein yeh na likho ke 'Wife ka naam faraham nahi kiya gaya'. "
        "Kisi ke walid ka naam nahi likhna. "
        "Mohtarma/Mohtarim ke neeche wala paragraph maximum 120 words ka ho, aur us mein reason ka khulasa ho. "
        "Notice mein court ka waqt: *subha 11 baje*, Location: *Shah Sahab ki Adalat*, aur aaj se do din baad ki tareekh likhni hai. "
        "Notice ke akhir mein '(Divorce Specialist ke hukum aur hidayat par)' ya kisi bhi tarah ka signature line nahi likhna."
    ),
    model=LitellmModel(model=MODEL, api_key=gemini_api_key)
)

@app.post("/send-whatsapp")
async def send_whatsapp(wifename: str = Form(None), husbandName: str = Form(None), reason: str = Form(None), phone: str = Form(None), address: str = Form(None)):
    form_data = DivorceFrom(wifeName=wifename, husbandName=husbandName, reason=reason, phone=phone, address=address)

    court_date = (datetime.now() + timedelta(days=2)).strftime("%d %B %Y")

    notice_prompt = (
        f"Wife ka naam: {form_data.wifeName if form_data.wifeName else 'Nahi diya gaya'}\n"
        f"Husband ka naam: {form_data.husbandName}\n"
        f"Reason: {form_data.reason}\n"
        f"Address: {form_data.address}\n"
        f"Date: {court_date}, Time: 11 baje, Location: Shah Sahab ki Adalat"
    )

    try:
        notice = await Runner.run(
            starting_agent=agent,
            input=notice_prompt
        )

        ultramsg_url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
        payload = {
            "token": TOKEN,
            "to": form_data.phone,
            "body": notice.final_output
        }
        headers = {'content-type': 'application/json'}
        response = requests.post(url=ultramsg_url, json=payload, headers=headers)

        if response.status_code == 200:
            return {"status": "success", "message": "WhatsApp message sent!"}
        else:
            return {"status": "error", "message": f"UltraMsg error: {response.text}"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}