from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import os
import json
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI

# Load env vars
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment variables.")

# FastAPI app
app = FastAPI()

# Init LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=1.0,
    google_api_key=api_key,
)

# Conversation memory
conversation_history = []

# System prompt
prompt = "You are a Chatbot integrated into the Finnish Nordea internet bank. You have access to the user's banking details (loans, cards, invoices)... [trimmed for brevity in this sample]"

# Input model
class ChatInput(BaseModel):
    message: str

# PDF/JSON preprocessing — optional for now
def process_pdf(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return ""

def process_json(file_path: str) -> str:
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    except Exception as e:
        print(f"Error processing JSON: {e}")
        return ""

# Pre-load content from files (optional)
pdf_content = process_pdf("../Invoice_ENG.pdf")
json_content = process_json("../mockdata.json")

if pdf_content:
    conversation_history.append({"role": "system", "content": f"PDF Content: {pdf_content}"})
if json_content:
    conversation_history.append({"role": "system", "content": f"JSON Content: {json_content}"})

conversation_history.insert(0, {"role": "system", "content": prompt})

# Endpoint
@app.post("/chat")
def chat_endpoint(chat_input: ChatInput):
    user_message = chat_input.message
    conversation_history.append({"role": "user", "content": user_message})

    response = llm.invoke(conversation_history)
    reply = response.content

    conversation_history.append({"role": "assistant", "content": reply})
    return {"response": reply}
