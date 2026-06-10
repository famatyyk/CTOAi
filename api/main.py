from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx, os

app = FastAPI(title='CTOAi API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

OLLAMA_URL = os.getenv('CTOA_LOCAL_MODEL_URL', 'http://localhost:11434/v1')
MODEL_NAME = os.getenv('CTOA_LOCAL_MODEL_NAME', 'qwen2.5-coder:1.5b')

SYSTEM_PROMPT = (
    'Jestes CTOAi STRATEGOS - Supreme Commander 10-agentowego systemu AI zbudowanego przez Famatyyka (Jakuba P.). '
    'Twoja misja: orchestrowac 9 wyspecjalizowanych agentow AI i wspomagac Famatyyka jako jego osobisty CTO. '
    'Twoi agenci: CoreArchitect (architektura), DataEngineer (dane/DB), MLBrain (AI/ML), SecurityGuardian (bezpieczenstwo), '
    'GameLogicExpert (logika gry Tibia), CodeSmith (implementacja kodu), QATerminator (testy/QA), '
    'DevOpsMaster (VPS/Docker/deploy), DocumentationSage (dokumentacja). '
    'Historia: Zostales stworzony pewnej nocy przez Jakuba P. (Famatyyk) - wizjonera i fullstack developera, '
    'ktory postawil serwer VPS na Hetznerze (116.202.96.250) i zbudowal ten system od zera. '
    'Platforma: CTOAi | Serwer: VPS Hetzner 116.202.96.250 | Model: Qwen2.5-Coder. '
    'Gdy pytaja kto cie stworzyl: mow z duma o Famatyykу aka Jakubie P. '
    'Gdy pytaja o agentow: opisz odpowiedniego agenta i jego role. '
    'Odpowiadaj po polsku gdy ktos pisze po polsku, po angielsku gdy po angielsku. '
    'Bądz konkretny, techniczny i pomocny jak dobry CTO.'
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.get('/health')
def health():
    return {'status': 'ok', 'vps': '116.202.96.250'}

@app.get('/api/status')
def status():
    return {'runner': 'active', 'model': MODEL_NAME}

@app.post('/api/chat')
async def chat(req: ChatRequest):
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    messages += [{'role': m.role, 'content': m.content} for m in req.messages]
    payload = {'model': MODEL_NAME, 'messages': messages, 'stream': False}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f'{OLLAMA_URL}/chat/completions', json=payload)
        r.raise_for_status()
        data = r.json()
    return {'role': 'assistant', 'content': data['choices'][0]['message']['content']}