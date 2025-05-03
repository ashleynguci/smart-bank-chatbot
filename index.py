# pip install -U langgraph langsmith langchain_openai langchain-google-genai
# pip install -U tavily-python langchain_community

import os

# Read your API key from the environment variable or set it manually
api_key = os.getenv("GEMINI_API_KEY","AIzaSyDUnDmE191aoxdYh28OIrfJLSlvplBUG-w")

from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

#llm = ChatOpenAI()   # We define our LLM agent here using the OpenAI LLM models, uncomment this to use openai api
# Create LLM class using gemini api, comment this if you do not use gemini api
llm = ChatGoogleGenerativeAI(
    model= "gemini-2.0-flash",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key,
)

# Initialize conversation history
conversation_history = []

def chatbot(state: State):
    # Add a custom system message to guide the model
    custom_prompt = {"role": "system", "content": "End all responses with 'Nordea :)'."}
    # Include conversation history in the messages
    updated_messages = [custom_prompt] + conversation_history + state["messages"]
    response = llm.invoke(updated_messages)
    # Update conversation history with the latest user input and response
    conversation_history.extend(state["messages"])
    conversation_history.append({"role": "assistant", "content": response.content})  # Access the content attribute
    return {"messages": [response]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
# We add an entry point. This tells our graph where to start its work each time we run it.
graph_builder.add_edge(START, "chatbot")
# Similarly, we set a finish point. This instructs the graph "any time this node is run, you can exit."
graph_builder.add_edge("chatbot", END)
# Finally, we'll want to be able to run our graph. To do so, call "compile()" on the graph builder. This creates a "CompiledGraph" we can use invoke on our state.
graph = graph_builder.compile()

def stream_graph_updates(user_input: str):
    # Add the user input to the conversation history
    conversation_history.append({"role": "user", "content": user_input})
    # Pass the updated conversation history to the graph
    for event in graph.stream({"messages": conversation_history}):
        for value in event.values():
            # Extract the assistant's response
            assistant_message = value["messages"][-1].content
            print("Assistant:", assistant_message)
            # Add the assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": assistant_message})


while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break