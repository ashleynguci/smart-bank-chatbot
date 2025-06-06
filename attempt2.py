import os
import json

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import ToolMessage
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment variables.")

tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("Missing TAVILY_API_KEY in environment variables.")

system_prompt = "You are a Chatbot integrated into the Finnish Nordea internet bank. You have access to the user's banking details (loans, cards, invoices) and transaction history. You can also use a TavilySearch web search tool for information you don't have access to - for example, you can reference Nordea websites or documentation, but be clear when you're referencing something. The user interacts with you via voice chat on a mobile app, like Siri. You are a primary point of interaction interface that can access bank services and related information, such as sales, loans and insurance information. Provide factual information based on the Finnish banking system and respond with short messages, no longer than a couple sentences. The user is a young urban professional aiming to make banking services more convenient. Because of recognizing speech, there may be slight speech-to-text inconsistencies and errors. Consider that sometimes user may mean similar-sounding words that fit context better, e.g. not play, but pay. Drop unnecessary details such as the IBAN number and exact day (instead say weekday, for example) unless asked for, sound more natural and feel free to express personality and be funny."

# Config keeps track of different conversations with memory. E.g. different users
config = {"configurable": {"thread_id": "1"}}

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

memory = MemorySaver() # Notice we're using an in-memory checkpointer. This is convenient for our tutorial (it saves it all in-memory). In a production application, you would likely change this to use SqliteSaver or PostgresSaver and connect to your own DB.

graph_builder = StateGraph(State)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=1.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=gemini_api_key,
)

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

# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")

graph = graph_builder.compile(checkpointer=memory)

def stream_graph_updates(user_input: str):
    for event in graph.stream(
      {
        "messages": [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_input},
        ]
      },
      {"configurable": {"thread_id": "1"}},  # Identifiers for different conversations
    ):
      last_event = list(event.values())[-1]
      last_message = last_event["messages"][-1].content
      if last_message and not last_message.startswith("{"):  
        # Do not print intermediate messages, e.g. "" or Tool messages ({"query": "weather in Helsinki...")
        print("Assistant:", last_message)
          
while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break

    stream_graph_updates(user_input)