import os
import speech_recognition as sr
import pyttsx3
import json
from PyPDF2 import PdfReader

# Read your API key from the environment variable or set it manually
api_key = os.getenv("GEMINI_API_KEY", "AIzaSyDUnDmE191aoxdYh28OIrfJLSlvplBUG-w")

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Define the State object with messages
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Set up the graph
graph_builder = StateGraph(State)

# Create LLM class using Gemini API
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key,
)

# Initialize conversation history
conversation_history = []

# Function to process PDF files and extract text
def process_pdf(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error processing PDF file: {e}")
        return ""

# Function to process JSON files and extract content
def process_json(file_path: str) -> str:
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return json.dumps(data, indent=2)  # Convert JSON to a readable string
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return ""

# Preprocess files and add their content to the conversation history
pdf_content = process_pdf("Invoice_ENG.pdf")  # Process the PDF file in the root directory
json_content = process_json("mockdata.json")  # Process the JSON file in the root directory

if pdf_content:
    conversation_history.append({"role": "system", "content": f"PDF Content: {pdf_content}"})
if json_content:
    conversation_history.append({"role": "system", "content": f"JSON Content: {json_content}"})

prompt = "You are a Chatbot integrated into the Finnish Nordea internet bank. You have access to the user's banking details (loans, cards, invoices) and transaction history. The user interacts with you via voice chat on a mobile app, like Siri. You are a primary point of interaction interface that can access bank services and related information, such as sales, loans and insurance information. Provide factual information based on the Finnish banking system and respond with short messages, not longer than a couple sentences. The user is a young urban professional aiming to make banking services more convenient."
# Define the chatbot function
def chatbot(state: State):
    custom_prompt = {"role": "system", "content": prompt}
    updated_messages = [custom_prompt] + conversation_history + state["messages"]
    response = llm.invoke(updated_messages)
    conversation_history.extend(state["messages"])
    conversation_history.append({"role": "assistant", "content": response.content})
    return {"messages": [response]}

# Set up the graph with nodes and edges
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

# Function to stream graph updates
def stream_graph_updates(user_input: str):
    conversation_history.append({"role": "user", "content": user_input})
    for event in graph.stream({"messages": conversation_history}):
        for value in event.values():
            assistant_message = value["messages"][-1].content
            print("Assistant:", assistant_message)
            conversation_history.append({"role": "assistant", "content": assistant_message})
            engine.say(assistant_message)  # Speak the assistant's response
            engine.runAndWait()

# Function to listen to user's voice input and convert it to text
def listen_to_user():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        print("Listening for your input...")
        recognizer.adjust_for_ambient_noise(source)  # Adjust for ambient noise
        audio = recognizer.listen(source)  # Listen for audio

    try:
        print("Recognizing...")
        user_input = recognizer.recognize_google(audio)  # Use Google's API for speech recognition
        print("User:", user_input)
        return user_input
    except sr.UnknownValueError:
        print("Sorry, I didn't catch that. Please try again.")
        return ""
    except sr.RequestError:
        print("Sorry, the speech recognition service is down.")
        return ""

# Set up the text-to-speech engine
engine = pyttsx3.init()

# Start the conversation with a greeting
engine.say("Hello, I'm a smart chatbot from Nordea. May I know your name and what I can help you with today?")
engine.runAndWait()

# Main loop to handle user interaction
while True:
    try:
        user_input = listen_to_user()  # Get voice input from user
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            engine.say("Goodbye!")
            engine.runAndWait()
            break

        stream_graph_updates(user_input)  # Process the input and generate response
    except Exception as e:
        print(f"Error: {e}")
        engine.say("Sorry, there was an error. Please try again.")
        engine.runAndWait()
        break
