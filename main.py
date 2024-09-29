from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from v1 import router as v1_router

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
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


# Include the v1 router
app.include_router(v1_router, prefix="/v1")

# Vercel requires a module named 'app' to be importable
app = app
