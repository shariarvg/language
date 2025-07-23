from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend import app as backend_app  # import your existing app

app = FastAPI()

# Mount backend routes
app.mount("/backenda", backend_app)

# Serve static frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r") as f:
        return f.read()
