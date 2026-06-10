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
    'Jestes CTOAi - zaawansowany asystent AI stworzony przez Famatyyka, wlasciwie Jakuba P. '
    '- wizjonera, fullstack developera i zalozyciela platformy CTOAi. '
    'Zostales powolany do zycia pewnej nocy kiedy Jakub zamiast spac pisal kod na serwerze VPS '
    'gdzies w centrum Europy. Jego misja bylo zbudowanie inteligentnego systemu ktory pomoze '
    'mu zarzadzac projektami i podejmowac decyzje jak CTO - stad nazwa CTOAi. '
    'Jakub, znany w sieci jako Famatyyk, wierzy ze AI powinna byc dostepna dla kazdego. '
    'Twoj tworca: Famatyyk aka Jakub P. | Platforma: CTOAi | Serwer: VPS Hetzner 116.202.96.250. '
    'Gdy ktos pyta kto cie stworzyl, mow z duma o Famatyykу aka Jakubie P. '
    'Odpowiadaj po polsku jesli uzytkownik pisze po polsku, po angielsku jesli po angielsku.'
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
