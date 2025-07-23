from fastapi import FastAPI, HTTPException, Depends

from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import bcrypt
import time
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Body
from db_tools import User
import whisper
from backend import router as backend_router
from db_tools import router as db_router
from db_tools import Base, engine, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_SECONDS
from fastapi.middleware.cors import CORSMiddleware


print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done.")


# App and routes
app = FastAPI()

# Allow local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def init_state():
    app.state.convo = {}  # dict: username -> scratchpad string

    # Load Whisper and conversation handler
    app.state.whisper_model = whisper.load_model("base")

app.include_router(backend_router)
app.include_router(db_router)


# Mount backend routes
#app.mount("/backend", backend_app)

# Serve static frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


print("app made")

@app.get("/")
def serve_index():
    return FileResponse("index.html")

@app.get("/history")
def serve_history():
    return FileResponse("history.html")
