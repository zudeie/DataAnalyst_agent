from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from tools import query_database, generate_visualization
from dotenv import load_dotenv

load_dotenv()
class Analyst_State(TypedDict):
    chart_json: str = ""
    messages: Annotated[list[BaseMessage], add_messages]

tools = [query_database,generate_visualization]

with open('system_prompt.md', 'r') as f:
    syst_prmt = f.read()

Analyst_agent = ChatOllama(model="qwen3:30b-a3b",
                       temperature=0.1,
                       num_ctx=8192,).bind_tools(tools)

def chatAnalyst(state: Analyst_State):
    messages = [SystemMessage(content=syst_prmt)] + state["messages"]
    response = Analyst_agent.invoke(messages)
    state.messages.append(response)
    return state
    

def routing(state: Analyst_State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph = StateGraph(Analyst_State)
graph.add_node("chatAnalyst", chatAnalyst)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "chatAnalyst")
graph.add_conditional_edges("chatAnalyst", routing, ["tools", END])
graph.add_edge("tools", "chatAnalyst")

Analyst__agent = graph.compile()

def invoke_agent(messg:str):
    result = Analyst__agent.invoke({"messages": [HumanMessage(content=messg)]})
    return result["messages"][-1].content

# def stream(mssg:str,"")
if __name__ == "__main__":
    test=invoke_agent("I want to analyze the sales data and visualize the trends.")
    print(test)

