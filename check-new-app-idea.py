from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pymongo import MongoClient
from bson import json_util
import os
import json
import sys

# Assuming you have set up your MongoDB connection string as an environment variable
MONGODB_URI = os.environ.get("MONGODB_URI")

# Set up MongoDB connection
client = MongoClient(MONGODB_URI)
db = client["app_ideas"]  # Replace with your database name
collection = db["ideas"]  # Replace with your collection name


# Update the state structure
class AgentState(TypedDict):
    original_prompt: str
    prompt_summary: str
    is_valid_app_idea: bool
    mongodb_result: str
    compare_result: str


# Define default models for each agent
# Some model options from OpenAI include:
# - gpt-3.5-turbo: A powerful model suitable for a wide range of tasks.
# - gpt-4: An advanced model with improved capabilities over previous versions.
# - gpt-3.5-turbo-instruct: A variant optimized for following instructions.
DEFAULT_EVAL_MODEL = "gpt-4o"
DEFAULT_COMPARE_MODEL = "gpt-4o"

# Create configurable ChatOpenAI instances
eval_model = ChatOpenAI(model_name=DEFAULT_EVAL_MODEL, temperature=0)
compare_model = ChatOpenAI(model_name=DEFAULT_COMPARE_MODEL, temperature=0)


# Add a new summarize_idea function
def summarize_idea(state: AgentState) -> AgentState:
    summarize_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an AI assistant that summarizes app ideas. Provide a concise one-sentence summary of the given app idea.",
            ),
            ("human", "{original_prompt}"),
        ]
    )
    summarize_chain = summarize_prompt | eval_model
    result = summarize_chain.invoke({"original_prompt": state["original_prompt"]})

    return {
        **state,
        "prompt_summary": result.content.strip(),
    }


# Modify the evaluate_idea function to validate the idea
def validate_idea(state: AgentState) -> AgentState:
    validate_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an AI assistant that evaluates app ideas. Determine if the given app idea is valid and feasible. Respond with 'Valid: Yes' or 'Valid: No' followed by a brief explanation.",
            ),
            ("human", "Original idea: {original_prompt}\nSummary: {prompt_summary}"),
        ]
    )
    validate_chain = validate_prompt | eval_model
    result = validate_chain.invoke(
        {
            "original_prompt": state["original_prompt"],
            "prompt_summary": state["prompt_summary"],
        }
    )

    is_valid = result.content.strip().startswith("Valid: Yes")

    return {
        **state,
        "is_valid_app_idea": is_valid,
    }


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
                "You are an AI assistant that evaluates app ideas. Provide a one-sentence summary of the idea, then determine if it's valid. Respond with 'Summary: [Your one-sentence summary]' followed by 'Valid: Yes' or 'Valid: No' on a new line.",
            ),
            ("human", "{original_prompt}"),
        ]
    )
    eval_chain = eval_prompt | eval_model
    result = eval_chain.invoke({"original_prompt": state["original_prompt"]})

    lines = result.content.split("\n")
    summary = next((line for line in lines if line.startswith("Summary:")), "")
    summary = summary.replace("Summary:", "").strip()
    is_valid = any("Valid: Yes" in line for line in lines)

    return {
        "original_prompt": state["original_prompt"],
        "is_valid_app_idea": is_valid,
        "prompt_summary": summary,
        "mongodb_result": "",
        "compare_result": "",
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
                "Compare the new app idea with existing ones. If it's unique, respond with 'INSERT'. If it's similar to an existing idea, respond with 'UPDATE: [existing idea]'. Provide your response on a single line.",
            ),
            (
                "human",
                "New idea: {prompt_summary}\nExisting ideas: {mongodb_result}",
            ),
        ]
    )
    compare_chain = compare_prompt | compare_model
    result = compare_chain.invoke(state)
    return {**state, "compare_result": result.content.strip()}


# Update the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("summarize_idea", summarize_idea)
workflow.add_node("validate_idea", validate_idea)
workflow.add_node("fetch_existing_ideas", fetch_existing_ideas)
workflow.add_node("compare_ideas", compare_ideas)

# Add edges
workflow.add_edge("summarize_idea", "validate_idea")
workflow.add_conditional_edges(
    "validate_idea", lambda x: "fetch_existing_ideas" if x["is_valid_app_idea"] else END
)
workflow.add_edge("fetch_existing_ideas", "compare_ideas")

# Set entry and finish points
workflow.set_entry_point("summarize_idea")
workflow.set_finish_point("compare_ideas")

# Compile the graph
app = workflow.compile()


# Function to process new app idea
def process_new_app_idea(idea: str) -> dict:
    result = app.invoke({"original_prompt": idea})

    if not result["is_valid_app_idea"]:
        return {
            "is_valid_app_idea": False,
            "prompt_summary": result["prompt_summary"],
        }

    compare_result = result["compare_result"]
    action = "INSERT" if compare_result.startswith("INSERT") else "UPDATE"
    existing_idea = compare_result.split(": ", 1)[1] if action == "UPDATE" else None

    if action == "INSERT":
        collection.insert_one({"idea": result["prompt_summary"], "votes": 1})
        output = {
            "is_valid_app_idea": True,
            "original_prompt": result["original_prompt"],
            "prompt_summary": result["prompt_summary"],
            "action_taken": action,
        }
    elif action == "UPDATE":
        existing_doc = collection.find_one_and_update(
            {"idea": existing_idea}, {"$inc": {"votes": 1}}, return_document=True
        )
        output = {
            "is_valid_app_idea": True,
            "original_prompt": result["original_prompt"],
            "prompt_summary": result["prompt_summary"],
            "action_taken": action,
            "matching_idea": existing_doc["idea"],
            "matching_idea_votes": existing_doc["votes"],
        }

    return output


# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python check-new-app-idea.py "Your app idea here"')
        sys.exit(1)

    new_idea = sys.argv[1]
    result = process_new_app_idea(new_idea)
    print(json.dumps(result, indent=2))

    # Close the MongoDB connection
    client.close()


# Add a function to update models if needed
def update_models(new_eval_model: str = None, new_compare_model: str = None):
    global eval_model, compare_model
    if new_eval_model:
        eval_model = ChatOpenAI(model_name=new_eval_model, temperature=0)
    if new_compare_model:
        compare_model = ChatOpenAI(model_name=new_compare_model, temperature=0)


# Example usage (if needed):
# update_models(new_eval_model="gpt-4", new_compare_model="gpt-3.5-turbo-16k")
