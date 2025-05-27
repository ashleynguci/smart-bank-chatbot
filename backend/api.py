# === Imports ===
import os
import json
import base64
from io import BytesIO
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Annotated
from typing_extensions import TypedDict
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from gtts import gTTS
from google.cloud import texttospeech

# === LangGraph & LangChain ===
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
# from langchain_core.messages import ToolMessage
# from langchain_openai import ChatOpenAI
# from langchain_tavily import TavilySearch
# from langchain.chat_models import init_chat_model
# from langgraph.prebuilt import ToolNode, tools_condition

# === Environment ===
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment variables.")

# === FastAPI App ===
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Replace with frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === State Definition ===
class State(TypedDict):
    messages: Annotated[list, add_messages]

memory = MemorySaver()
graph_builder = StateGraph(State)

# === LLM Init ===
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key,
)

# === System Prompt ===
prompt = """You are a Chatbot integrated into the Finnish Nordea internet bank. 
You have access to the user's banking details (loans, cards, invoices) and transaction history... [truncated for brevity]
"""

# === LLM Node (Chatbot) ===
def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# === Tool-based Agent (NOT ENABLED YET) ===
'''
tool = TavilySearch(max_results=2)
tools = [tool]
llm_with_tools = llm.bind_tools(tools)

class BasicToolNode:
    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        message = inputs.get("messages", [])[-1]
        outputs = []
        for tool_call in message.tool_calls:
            result = self.tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            outputs.append(ToolMessage(
                content=json.dumps(result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            ))
        return {"messages": outputs}

tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

def route_tools(state: State):
    messages = state.get("messages", [])
    ai_message = messages[-1] if messages else None
    if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
        return "tools"
    return END

graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
'''

graph = graph_builder.compile(checkpointer=memory)

# === Streaming Graph Execution ===
def stream_graph_updates(user_input: str, id: str):
    for event in graph.stream(
        {
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ]
        },
        {"configurable": {"thread_id": id}},
    ):
        last_event = list(event.values())[-1]
        last_message = last_event["messages"][-1].content
        if last_message and not last_message.startswith("{"):
            print("Assistant:", last_message)
            return last_message

# === Input Schema ===
class ChatInput(BaseModel):
    message: str
    userId: str
    audio: bool

# === File Processing (Optional) ===
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

pdf_content = process_pdf("data/Invoice_ENG.pdf")
json_content = process_json("data/mockdata.json")
document_context = []

if pdf_content:
    document_context.append({"role": "system", "content": f"PDF Content: {pdf_content}"})
if json_content:
    document_context.append({"role": "system", "content": f"JSON Content: {json_content}"})

# === Text-to-Speech ===
# def text_to_base64_audio(text: str, lang: str = "en") -> str:
#     tts = gTTS(text=text, lang=lang)
#     audio_fp = BytesIO()
#     tts.write_to_fp(audio_fp)
#     audio_fp.seek(0)
#     return base64.b64encode(audio_fp.read()).decode("utf-8")

def text_to_base64_audio(text: str, lang: str = "en-US") -> str:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=lang,
        name="en-US-Chirp3-HD-Achernar",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return base64.b64encode(response.audio_content).decode("utf-8")

# === API Endpoint ===
@app.post("/chat")
def chat_endpoint(chat_input: ChatInput):
    print("User:", chat_input)
    user_message = chat_input.message
    user_id = chat_input.userId
    audio = chat_input.audio

    # Hardcoded structured response examples
    # Link and attachment messages are not added to memory, AI won't be aware of them yet.
    # Refer to this https://python.langchain.com/docs/concepts/structured_outputs/ 
    # on how to create structured outputs with Langchain/LangGraph.
    
    if user_message == "link":
        return {
            "response": [
                {"type": "text", "content": "Based on ASP loan terms "},
                {"type": "link", "url": "https://www.nordea.fi/en/personal/our-services/loans/home-loans/asploan.html#faq=Frequently-asked-questions-about-ASP-loans+496407", "label": "Nordea - ASP loan"},
                {"type": "text", "content": ", The saving period for an ASP loan is a minimum of two years. Let me know if you need anything else."}
            ]
        }
    elif user_message == "attachment":
        return {
            "response": [
                {"type": "text", "content": "You have 1 unpaid invoice from SlicedInvoices: "},
                {"type": "attachment", "url": "https://slicedinvoices.com/pdf/wordpress-pdf-invoice-plugin-sample.pdf", "label": "Open Invoice PDF"},
                {"type": "text", "content": "The due date is this Wednesday, and the sum is 93.50€."}
            ]
        }

    reply = stream_graph_updates(user_message, user_id)
    response = [{"type": "text", "content": reply}]
    if audio:
        response.append({
            "type": "audio",
            "content": text_to_base64_audio(reply),
            "format": "mp3"
        })
    return {"response": response}
