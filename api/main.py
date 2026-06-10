from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CTOAi API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "vps": "116.202.96.250"}

@app.get("/api/status")
def status():
    return {"runner": "active", "model": "qwen2.5-coder:1.5b"}
