from fastapi import FastAPI

app = FastAPI()


@app.get("/api/hello")
async def read_root():
    return {"message": "Hello from Vercel!"}


# Vercel requires a module named 'app' to be importable
app = app
