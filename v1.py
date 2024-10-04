from fastapi import APIRouter, HTTPException
from utils.check_new_app_idea import process_new_app_idea

router = APIRouter()


@router.get("/hello")
async def read_root():
    return {"message": "Hello from Vercel!"}


@router.post("/v1/new-app-idea")
async def new_app_idea(idea: dict):
    if "idea" not in idea:
        raise HTTPException(
            status_code=400, detail="Missing 'idea' field in request body"
        )

    new_idea = idea["idea"]
    result = process_new_app_idea(new_idea)

    return result
