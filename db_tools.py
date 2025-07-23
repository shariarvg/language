from jose import JWTError, jwt
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi import Request
import bcrypt
import time
from datetime import datetime
import os
from sqlalchemy.orm import relationship
import json
SECRET_KEY = os.environ['SECRET_KEY']  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour
from typing import List
from sqlalchemy.ext.mutable import MutableList

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    scratchpad = Column(MutableList.as_mutable(JSON), default=list)
    conversation_history = Column(MutableList.as_mutable(JSON), default=list)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")

class ConversationMeta(BaseModel):
    id: int
    timestamp: str
    scratchpad: List[str]

class ConversationDetail(BaseModel):
    id: int
    timestamp: str
    scratchpad: List[str]
    conversation_history: List[dict]


# DB setup
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

router = APIRouter()

# Auth helpers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    username: str
    password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hash_password(user.password)
    db_user = User(username=user.username, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    return {"msg": "User created"}

@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    convo = Conversation(user_id = user.id, scratchpad = [], conversation_history = [])
    db.add(convo)
    db.commit()
    db.refresh(convo)

    token_data = {
        "sub": user.username,
        "convo_id": convo.id
    }
    token = create_token(token_data)

    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def read_me(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    return {"username": payload.get("sub")}

@router.post("/scratchpad")
def save_existing_convo(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    username = decode_token(token).get("sub")

    convo_state = request.app.state.convo.get(username)
    if not convo_state:
        raise HTTPException(status_code=400, detail="No active conversation found")

    convo_id = convo_state["id"]
    scratchpad = convo_state["scratchpad"]

    convo = db.query(Conversation).filter(Conversation.id == convo_id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    convo.scratchpad = scratchpad
    db.commit()
    return {"msg": "Scratchpad updated"}

@router.get("/scratchpad")
def get_scratchpad(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_token(token)
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"scratchpad": user.scratchpad}

@router.get("/conversations", response_model=List[ConversationMeta])
def get_user_conversations(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")

    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    conversations = db.query(Conversation)\
        .filter(Conversation.user_id == user.id)\
        .order_by(Conversation.timestamp.desc())\
        .all()

    return [
        ConversationMeta(
            id=conv.id,
            timestamp=conv.timestamp.isoformat(),
            scratchpad=conv.scratchpad
        ) for conv in conversations
    ]

@router.get("/conversations/{convo_id}", response_model=ConversationDetail)
def get_conversation(convo_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")

    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    conversation = db.query(Conversation).filter_by(id=convo_id, user_id=user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    print(conversation.conversation_history)
    print(conversation.scratchpad)


    return ConversationDetail(
        id=conversation.id,
        timestamp=conversation.timestamp.isoformat(),
        scratchpad=conversation.scratchpad,
        conversation_history=conversation.conversation_history
    )