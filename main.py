import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize MongoDB client
MONGODB_URI = os.environ.get("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["app_ideas"]  # Replace with your actual database name
app_ideas_collection = db["ideas"]  # Replace with your actual collection name


@app.get("/", response_class=HTMLResponse)
async def root():
    # Existing HTML response
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API of Dreams</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                background-color: black;
                color: #39ff14;
                font-family: Arial, sans-serif;
            }
            h1 {
                font-size: 3rem;
            }
            p {
                font-size: 1.2rem;
            }
        </style>
    </head>
    <body>
        <h1>API of Dreams</h1>
        <p>There is no website available here, this is just the api. For help visit <a href="https://www.dotdev.dev">www.dotdev.dev</a></p>
    </body>
    </html>
    """


@app.post("/v1/app-ideas/new")
async def new_app_idea(idea: dict):
    if "idea" not in idea:
        raise HTTPException(
            status_code=400, detail="Missing 'idea' field in request body"
        )

    new_idea = idea["idea"]
    result = process_new_app_idea(new_idea)

    return result


@app.post("/v1/app-ideas/vote")
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


@app.get("/v1/app-ideas/all")
async def get_all_app_ideas():
    # Retrieve all app ideas from the database
    app_ideas = list(app_ideas_collection.find())

    # Convert ObjectId to string for JSON serialization
    for idea in app_ideas:
        idea["_id"] = str(idea["_id"])

    return {"app_ideas": app_ideas}


# Vercel requires a module named 'app' to be importable
app = app
