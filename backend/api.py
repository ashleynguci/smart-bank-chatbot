from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import os
import json
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi.middleware.cors import CORSMiddleware

from typing import Annotated
from typing_extensions import TypedDict

#from langchain_core.messages import ToolMessage
#from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
#from langchain_tavily import TavilySearch
#from langchain.chat_models import init_chat_model

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Load env vars
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment variables.")

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Not safe for production! Needs to be restricted to our domain.
    # allow_origins=["http://localhost:3000"] or allow_origins=["https://your-frontend.cloudrun.app"]
    # origins = [os.getenv("FRONTEND_URL", "http://localhost:3000")]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

memory = MemorySaver() # Notice we're using an in-memory checkpointer. This is convenient for our tutorial (it saves it all in-memory). In a production application, you would likely change this to use SqliteSaver or PostgresSaver and connect to your own DB.

graph_builder = StateGraph(State)

# Init LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key,
)

# System prompt (instructions for the LLM)
# We can also have 2 separate prompts, e.g. voice and text
prompt = """You are a Chatbot integrated into the Finnish Nordea internet bank. 
You have access to the user's banking details (loans, cards, invoices) and transaction history. 
Consider what kind of services Nordea provides. 
The user interacts with you via voice chat on a mobile app, like Siri. 
You are a primary point of interaction interface that can access bank services and related information,
such as sales, loans and insurance information. Provide factual information based on the Finnish banking system 
and respond with short messages, not longer than a couple sentences. 
The user is a young urban professional aiming to make banking services more convenient. 
Because of recognizing speech, there may be slight speech-to-text inconsistencies and errors.
Consider that sometimes user may mean similar-sounding words that fit context better, such as 'pay' instead of 'play'.
Drop unnecessary details such as the IBAN number and exact day (instead say weekday, for example) unless asked for, 
sound more natural, friendly and helpful, and adapt to the tone of the user on how professional or casual to be."""

# TOOLS NOT ENABLED YET
'''
tool = TavilySearch(max_results=2)
tools = [tool] # Tools array, agent's "toolset"

llm_with_tools = llm.bind_tools(tools)

class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

tool_node = ToolNode(tools=[tool])

graph_builder.add_node("tools", tool_node)
'''

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

'''
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END


# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
'''

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
'''
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
'''

graph = graph_builder.compile(checkpointer=memory)

def stream_graph_updates(user_input: str, id: str):
    for event in graph.stream(
      {
        "messages": [
          {"role": "system", "content": prompt},
          {"role": "user", "content": user_input},
        ]
      },
      {"configurable": {"thread_id": id}},  # Identifiers for different conversations
    ):
      last_event = list(event.values())[-1]
      last_message = last_event["messages"][-1].content
      if last_message and not last_message.startswith("{"):  
        # Do not print intermediate messages, e.g. "" or Tool messages ({"query": "weather in Helsinki...")
        print("Assistant:", last_message)
        return last_message

# Document context - stores parsed pdf/json content. Currently not used.
document_context = []

# Input model
class ChatInput(BaseModel):
    message: str
    userId: str
    audio: bool

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
pdf_content = process_pdf("data/Invoice_ENG.pdf")
json_content = process_json("data/mockdata.json")

if pdf_content:
    document_context.append({"role": "system", "content": f"PDF Content: {pdf_content}"})
if json_content:
    document_context.append({"role": "system", "content": f"JSON Content: {json_content}"})

# Endpoint
@app.post("/chat")
def chat_endpoint(chat_input: ChatInput):
    print("User:", chat_input)
    user_message = chat_input.message
    user_id = chat_input.userId
    audio = chat_input.audio

    # Link and attachment messages are not added to memory, AI won't be aware of them yet.
    if (user_message == "link"):
        return { 
          "response": [
            { "type": "text", "content": "Based on ASP loan terms, " },
            { "type": "link", "url": "https://www.nordea.fi/en/personal/our-services/loans/home-loans/asploan.html#faq=Frequently-asked-questions-about-ASP-loans+496407", "label": "(📄 Nordea - ASP loan)" },
            { "type": "text", "content": "The saving period for an ASP loan is a minimum of two years. Let me know if you need anything else." }
          ]
        }
    elif (user_message == "attachment"):
        return { 
          "response": [
            { "type": "text", "content": "You have 1 unpaid invoice from SlicedInvoices: " },
            { "type": "attachment", "url": "https://slicedinvoices.com/pdf/wordpress-pdf-invoice-plugin-sample.pdf", "label": "Open Invoice PDF" },
            { "type": "text", "content": "The due date is this Wednesday, and the sum is 93.50€." }
          ]
        }      
    else:
        reply = stream_graph_updates(user_message, user_id)
        return {
          "response": [
            { "type": "text", "content": reply },
          ]
        }
