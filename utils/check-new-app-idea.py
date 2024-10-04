from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pymongo import MongoClient
from bson import json_util
import os
import json

# Assuming you have set up your MongoDB connection string as an environment variable
MONGODB_URI = os.environ.get("MONGODB_URI")

# Set up MongoDB connection
client = MongoClient(MONGODB_URI)
db = client["app_ideas"]  # Replace with your database name
collection = db["ideas"]  # Replace with your collection name


# Define the state structure
class AgentState(TypedDict):
    original_prompt: str
    is_valid_app_idea: bool
    user_prompt_summary: str
    mongodb_result: str
    compare_result: str


# Create the evaluation agent
eval_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI assistant that evaluates app ideas. Summarize the idea and determine if it's valid.",
        ),
        ("human", "{original_prompt}"),
    ]
)


# Modify the evaluate_idea node
def evaluate_idea(state: AgentState) -> AgentState:
    eval_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an AI assistant that evaluates app ideas. Summarize the idea and determine if it's valid.",
            ),
            ("human", "{original_prompt}"),
        ]
    )
    eval_chain = eval_prompt | ChatOpenAI(temperature=0)
    result = eval_chain.invoke({"original_prompt": state["original_prompt"]})
    return {
        "original_prompt": state["original_prompt"],
        "is_valid_app_idea": "yes" in result.content.lower(),
        "user_prompt_summary": result.content[:200],
        "mongodb_result": state.get("mongodb_result", ""),
        "compare_result": state.get("compare_result", ""),
    }


# Modify the fetch_existing_ideas node
def fetch_existing_ideas(state: AgentState) -> AgentState:
    mongodb_result = json.dumps(list(collection.find()), default=json_util.default)
    return {**state, "mongodb_result": mongodb_result}


# Modify the compare_ideas node
def compare_ideas(state: AgentState) -> AgentState:
    compare_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Compare the new app idea with existing ones. If it's unique, say 'INSERT'. If it exists, say 'UPDATE'.",
            ),
            (
                "human",
                "New idea: {user_prompt_summary}\nExisting ideas: {mongodb_result}",
            ),
        ]
    )
    compare_chain = compare_prompt | ChatOpenAI(temperature=0)
    result = compare_chain.invoke(state)
    return {**state, "compare_result": result.content}


# Define the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("evaluate_idea", evaluate_idea)
workflow.add_node("fetch_existing_ideas", fetch_existing_ideas)
workflow.add_node("compare_ideas", compare_ideas)

# Add edges
workflow.add_edge("evaluate_idea", "fetch_existing_ideas")
workflow.add_edge("fetch_existing_ideas", "compare_ideas")

# Set entry and finish points
workflow.set_entry_point("evaluate_idea")
workflow.set_finish_point("compare_ideas")

# Compile the graph
app = workflow.compile()


# Function to process new app idea
def process_new_app_idea(idea: str) -> dict:
    result = app.invoke({"original_prompt": idea})

    # The result is now the final state of the workflow
    if result["compare_result"] == "INSERT":
        collection.insert_one({"idea": result["user_prompt_summary"], "votes": 1})
    elif result["compare_result"] == "UPDATE":
        collection.update_one(
            {"idea": result["user_prompt_summary"]},
            {"$inc": {"votes": 1}},
        )

    return {
        "is_valid_app_idea": result["is_valid_app_idea"],
        "user_prompt_summary": result["user_prompt_summary"],
        "action_taken": result["compare_result"],
    }


# Example usage
if __name__ == "__main__":
    new_idea = "an app about dressing up dolls"
    result = process_new_app_idea(new_idea)
    print(result)

    # Close the MongoDB connection
    client.close()
