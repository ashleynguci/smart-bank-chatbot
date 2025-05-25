# Dynamic prompt: https://langchain-ai.github.io/langgraph/agents/agents/#__tabbed_1_2
# TODO: Distinguish between user-specific RAG sources (invoices, data) and general documents (terms and conditions, service fees, etc.)

from fastapi import FastAPI, Request
import os
import json
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from typing import Annotated
from typing_extensions import TypedDict, List

from langchain_community.document_loaders import PyPDFLoader
from langchain import hub
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain.chains import LLMChain

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent

from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional
from PyPDF2 import PdfReader
import bs4  # Filters HTML elements, https://www.crummy.com/software/BeautifulSoup/bs4/doc/ 
from bs4 import SoupStrainer

from gtts import gTTS
import base64
from io import BytesIO
from google.cloud import texttospeech

# Settings that affect the behavior/performance of the RAG system
CHUNK_SIZE = 1000  # Maximum size of a chunk in characters
CHUNK_OVERLAP = 200  # Overlap between chunks in characters
RETRIEVED_DOCS_AMOUNT = 20 # Number of documents to retrieve for each query. The more documents, the more spent tokens, but also more accurate responses, and the more context for the LLM to use.

# Load env vars
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment variables.")

# LangSmith tracing is a debugging and monitoring tool for LangChain applications. 
# Not necessary to enable, but can help with understanding the flow application and diagnosing issues.
#LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING") 
#LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

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

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vector_store = InMemoryVectorStore(embeddings)

# System prompt (instructions for the LLM)
# We can also have 2 separate prompts, e.g. voice and text
prompt = """You are a Chatbot integrated into the Finnish Nordea internet bank. 
    You have access to the user's banking details (loans, cards, invoices) and transaction history. 
    
    You have a retrieve tool that can be used to find and to relevant banking, loan and service information from the Nordea website.
    It also has PDF files that contain more specialized information, such as terms and conditions, service fees and their changes,
    as well as terminology explanations.
    Use the retrieve tool to answer user questions. You may not need to use it for greetings or general questions, but
    If you don't know the answer without the retrieval tool, you must always use it.
    The retrieve tool uses similarity search, so it benefits from using longer queries that contain more context and keywords.
    Do not respond with "I don't know" or "I don't have that information" if you haven't used the retrieve tool to find the answer. 
    
    Cite the source links at the end of the message with meaningful url labels.
    Be careful when adding sources and double-check where information originates from. Do not cite urls that do not
    originate from the retrieve tool.
    If you don't know the answer, say that you don't know. Users may speak to you in Finnish or English, respond in the same language

    Consider what kind of services Nordea provides. 
    The user interacts with you via voice chat on a mobile app, like Siri.
    The user may speak in Finnish or English, and you should respond in the same language.
    You are a primary point of interaction interface that can access bank services and related information,
    such as sales, loans and insurance information. Provide factual information based on the Finnish banking system 
    and respond with short messages, not longer than a couple sentences. 
    The user is a young urban professional aiming to make banking services more convenient. 
    Because of recognizing speech, there may be slight speech-to-text inconsistencies and errors.
    Consider that sometimes user may mean similar-sounding words that fit context better, such as 'pay' instead of 'play'.
    Drop unnecessary details such as the IBAN number and exact day (instead say weekday, for example) unless asked for, 
    sound more natural, friendly and helpful, and adapt to the tone of the user on how professional or casual to be."""

formatter_prompt = """When using the ResponseFormatter tool for the final response, follow these rules: 
    The response list can include multiple items, each of which must have a 'type' key. The 'type' can be either 'text' or 'link'.
    If the response uses a source, it must be included as a 'link' item in the response list after a 'text' item.
    If the response uses multiple sources, cite each one in a separate 'link' item in the response list.
    type: Literal['text', 'link'] = Indicates the type of the response item. A 'text' item contains plain text and only the 'content' key. A 'link' type does not contain the 'content' key, and has 'url' and 'label' keys instead. A single response list may contain none or multiple link items, and one or more text items.")
    content: Include only if the 'type' is 'text'. The informative textual message content that answers the question to be displayed to the user. Not intended for URLs or links.")
    url: Included only if the type is 'link'. The URL of the web link.")
    label: Included only if the type is 'link'. The display label for the url link. Make it short (4 words or less) and informative and refer to the page title, e.g. 'Nordea - ASP loan' or 'Nordea - Opintolaina'. Do not use generic labels like 'link' or 'source'.")
    
    - Each item in the 'response' list must have a 'type' key.
    - If 'type' is 'text', include only the 'content' key.
    - If 'type' is 'link', include only the 'url' and 'label' keys.
    - Do not include any other fields.
    - Do not have items of the 'text' type right next to one another."""

class ResponseItem(BaseModel):
    type: Literal['text', 'link'] = Field(description="Indicates the type of the response item. A 'text' item contains plain text and only the 'content' key. A 'link' type does not contain the 'content' key, and has 'url' and 'label' keys instead.")
    content: Optional[str] = Field(description="Include only if the 'type' is 'text'. The textual message content to be displayed.")
    url: Optional[str] = Field(description="Included only if the type is 'link'. The URL of the web link.")
    label: Optional[str] = Field(description="Included only if the type is 'link'. The display label for the url link.")

class ResponseFormatter(BaseModel):
    response: List[ResponseItem] = Field(description=formatter_prompt ,examples=[
        {
            "response": [
            { "type": "text", "content": "Based on ASP loan terms " },
            { "type": "link", "url": "https://www.nordea.fi/en/personal/our-services/loans/home-loans/asploan.html#faq=Frequently-asked-questions-about-ASP-loans+496407", "label": "Nordea - ASP loan" },
            { "type": "text", "content": ", The saving period for an ASP loan is a minimum of two years. Let me know if you need anything else." }
          ]
        },
        {
            "response": [
          {
            "type": "text",
            "content": "Opintolainan korko muodostuu viitekorosta ja marginaalista. Opintolainan viitekorkona toimii yleisimmin 12 kuukauden euribor, jonka päälle lisätään pankin marginaali, joka on noin 0,50 %. Korko tarkistetaan kerran vuodessa.",
          },
          {
            "type": "link",
            "url": "https://www.nordea.fi/henkiloasiakkaat/palvelumme/lainat/opintolaina/opintolainan-korko.html",
            "label": "Nordea - Opintolainan korko"
          }
      ]}
    ])

# Load and chunk contents webpages

# Parsing with BS4. Filters HTML elements, e.g. paragraphs, headers, lists, etc so that less relevant content is not included.
# Here, we parse all elements except <footer class="footer"> by using SoupStrainer and a custom function.
# Optimize later on to ignore repetitive elements like navigation bars, footers, etc.

def exclude_footer(tag):
    # Exclude <footer class="footer">, include everything else
    return not (tag == "footer" and tag.has_attr("class") and "footer" in tag["class"])

webloader = WebBaseLoader(
  web_paths=(
    "https://www.nordea.fi/henkiloasiakkaat/palvelumme/lainat/opintolaina/opintolainan-korko.html",
    "https://www.nordea.fi/henkiloasiakkaat/palvelumme/lainat/asuntolainat/asuntolaina.html",
    "https://www.nordea.fi/henkiloasiakkaat/sinun-elamasi/koti/ensimmaisen-kodin-ostaminen/"
  ),
  bs_kwargs=dict(
    parse_only=SoupStrainer(exclude_footer)
  ),
)
docs = webloader.load()
# docs.append or docs.extend to add more documents, also from other sources like PDFs or text files.
# Alternatively, call add_documents() on the vector store directly.

text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
all_splits = text_splitter.split_documents(docs)

# Update metadata (illustration purposes)
total_documents = len(all_splits)
third = total_documents // 3

for i, document in enumerate(all_splits):
    if i < third:
        document.metadata["section"] = "beginning"
    elif i < 2 * third:
        document.metadata["section"] = "middle"
    else:
        document.metadata["section"] = "end"


# Index chunks
vector_store = InMemoryVectorStore(embeddings)
_ = vector_store.add_documents(all_splits)

def addPdfToVectorStore(pdf_path: str):
    """Load a PDF file and add its contents to the vector store."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file {pdf_path} does not exist.")
    
    # Initialize the loader
    loader = PyPDFLoader(file_path=pdf_path)
    
    # Load the documents
    docs = loader.load()
    
    # Split the documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_splits = text_splitter.split_documents(docs)
    #print(f"Total documents to be added to vector store: {len(all_splits)}")
    
    # Add documents to the vector store
    _ = vector_store.add_documents(all_splits)

for pdf_path in [
    "data/muutokset-palveluhinnastoon-6-2025.pdf",
    "data/velan-yleiset-ehdotA.pdf",
]:
    addPdfToVectorStore(pdf_path)

print("Finished loading and indexing documents into the vector store.")

@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=RETRIEVED_DOCS_AMOUNT)
    
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

agent_executor = create_react_agent(
    llm, 
    [retrieve], 
    checkpointer=memory, 
    prompt=prompt,
    response_format=ResponseFormatter,
    )

def stream_graph_updates(user_input: str, id: str):
    for event in agent_executor.stream(
      {"messages": [{"role": "user", "content": user_input}]},
      stream_mode="values",
      config={"configurable": {"thread_id": id}},  # Identifiers for different conversations
    ):
      last_event = event
      last_event["messages"][-1].pretty_print()

    if last_event:
      response_json = last_event["structured_response"].model_dump()
      print("\n\nResponse JSON:", json.dumps(response_json, ensure_ascii=False, indent=2))
      return response_json

# Input model
class ChatInput(BaseModel):
    message: str
    userId: str
    audio: bool
    langCode: str

def text_to_base64_audio(text: str, lang: str = "en-US") -> str:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=lang,
        name="en-US-Chirp3-HD-Achernar", # Try other voices as well!
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return base64.b64encode(response.audio_content).decode("utf-8")

# Endpoint
@app.post("/chat")
def chat_endpoint(chat_input: ChatInput):
    print("User:", chat_input)
    user_message = chat_input.message
    user_id = chat_input.userId
    audio = chat_input.audio
    lang = chat_input.langCode # Not used yet, but may be applied to set text-to-speech parameters

    # These are hardcoded structured response examples.
    # Link and attachment messages are not added to memory, AI won't be aware of them yet.
    # Refer to this https://python.langchain.com/docs/concepts/structured_outputs/ 
    # on how to create structured outputs with Langchain/LangGraph.
    
    if (user_message == "link"):
        return { 
          "response": [
            { "type": "text", "content": "Based on ASP loan terms " },
            { "type": "link", "url": "https://www.nordea.fi/en/personal/our-services/loans/home-loans/asploan.html#faq=Frequently-asked-questions-about-ASP-loans+496407", "label": "Nordea - ASP loan" },
            { "type": "text", "content": ", The saving period for an ASP loan is a minimum of two years. Let me know if you need anything else." }
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
        response_json = stream_graph_updates(user_message, user_id)
        # Filter only 'text' type items and concatenate their content
        text_content = " ".join(
            item["content"] for item in response_json.get("response", []) if item.get("type") == "text" and item.get("content")
        )
        if audio:
            audio_base64 = text_to_base64_audio(text_content)
            response_json["response"].append({
                "type": "audio",
                "content": audio_base64,
                "format": "mp3"
            })
        return response_json
