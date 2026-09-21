from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_ollama import ChatOllama   
from langchain.agents import create_agent
from tools import query_database,generate_visualization
from dotenv import load_dotenv

load_dotenv()
class Analyst_State(BaseModel):
    chart_json:str =""
    messages: Annotated[list[BaseMessage], add_messages]

tools = [query_database,generate_visualization]

with open('system_prompt.md', 'r') as f:
    syst_prmt = f.read()

llm = ChatOllama(model="qwen3:14b",
                       temperature=0.1,
                       num_ctx=8192,)

Analyst_agent = create_agent(llm, tools=tools, system_prompt=syst_prmt)

def chatAnalyst(state: Analyst_State):
    response = Analyst_agent.invoke(state.messages)
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
    result = Analyst__agent.invoke(HumanMessage(content=messg))
    return result["messages"][-1].content

# def stream(mssg:str,"")