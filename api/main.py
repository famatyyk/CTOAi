from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import os

app = FastAPI(title="CTOAi API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("CTOA_LOCAL_MODEL_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("CTOA_LOCAL_MODEL_NAME", "qwen2.5-coder:1.5b")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


@app.get("/health")
def health():
    return {"status": "ok", "vps": "116.202.96.250"}


@app.get("/api/status")
def status():
    return {"runner": "active", "model": MODEL_NAME}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{OLLAMA_URL}/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()
    content = data["choices"][0]["message"]["content"]
    return {"role": "assistant", "content": content}
