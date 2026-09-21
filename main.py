from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama   
from tools import query_database
from dotenv import load_dotenv

load_dotenv()
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

tools = [query_database]

llmwtools = ChatOllama(model="qwen3:14b",
                       temperature=0,
                       num_ctx=8192,).bind_tools(tools)

def chatbot(state: State):
    return {"messages": [llmwtools.invoke(state["messages"])]}

def should_continue(state: State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", should_continue, ["tools", END])
graph.add_edge("tools", "chatbot")

agent = graph.compile()