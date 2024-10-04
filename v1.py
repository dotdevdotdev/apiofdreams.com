from fastapi import APIRouter, HTTPException
from ..utils.check_new_app_idea import process_new_app_idea
from pymongo import MongoClient
from bson import ObjectId

router = APIRouter()

# Initialize MongoDB client (you may want to move this to a separate config file)
client = MongoClient("your_mongodb_connection_string")
db = client["your_database_name"]
app_ideas_collection = db["app_ideas"]


@router.post("/v1/app-ideas/new")
async def new_app_idea(idea: dict):
    if "idea" not in idea:
        raise HTTPException(
            status_code=400, detail="Missing 'idea' field in request body"
        )

    new_idea = idea["idea"]
    result = process_new_app_idea(new_idea)

    return result


@router.post("/v1/app-ideas/vote")
async def vote_app_idea(idea_id: dict):
    if "ideaId" not in idea_id:
        raise HTTPException(
            status_code=400, detail="Missing 'ideaId' field in request body"
        )

    idea_id_str = idea_id["ideaId"]

    try:
        # Convert string to ObjectId
        idea_object_id = ObjectId(idea_id_str)
    except:
        raise HTTPException(status_code=400, detail="Invalid ideaId format")

    # Increment the vote count
    result = app_ideas_collection.update_one(
        {"_id": idea_object_id}, {"$inc": {"votes": 1}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="App idea not found")

    return {"message": "Vote recorded successfully"}


@router.get("/v1/app-ideas")
async def get_all_app_ideas():
    # Retrieve all app ideas from the database
    app_ideas = list(app_ideas_collection.find())

    # Convert ObjectId to string for JSON serialization
    for idea in app_ideas:
        idea["_id"] = str(idea["_id"])

    return {"app_ideas": app_ideas}
