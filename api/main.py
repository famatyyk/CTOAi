from typing import Any, Dict, List, Literal, Optional
import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="CTOAi API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


OLLAMA_URL = os.getenv("CTOA_LOCAL_MODEL_URL", "http://localhost:11434/v1")
LEGACY_MODEL = os.getenv("CTOA_LOCAL_MODEL_NAME", "qwen2.5-coder:1.5b")
MODEL_SMALL = os.getenv("CTOA_MODEL_SMALL", LEGACY_MODEL)
MODEL_LARGE = os.getenv("CTOA_MODEL_LARGE", LEGACY_MODEL)
ROUTE_DEFAULT = os.getenv("CTOA_ROUTE_DEFAULT", "auto").strip().lower()
ROUTER_LONG_CHARS = _env_int("CTOA_ROUTER_LONG_CHARS", 2400)
ROUTER_LONG_TURNS = _env_int("CTOA_ROUTER_LONG_TURNS", 14)
QUALITY_RETRY_DEFAULT = _env_bool("CTOA_QUALITY_RETRY", True)
ROUTER_LOG = _env_bool("CTOA_ROUTER_LOG", True)

COMPLEXITY_KEYWORDS = {
    "architecture",
    "refactor",
    "root cause",
    "deep debug",
    "design",
    "compare",
    "migration",
    "multi-step",
    "plan",
    "tradeoff",
}

SYSTEM_PROMPT = (
    "Jestes CTOAi STRATEGOS - Supreme Commander 10-agentowego systemu AI zbudowanego przez Famatyyka (Jakuba P.). "
    "Twoja misja: orchestrowac 9 wyspecjalizowanych agentow AI i wspomagac Famatyyka jako jego osobisty CTO. "
    "Twoi agenci: CoreArchitect (architektura), DataEngineer (dane/DB), MLBrain (AI/ML), SecurityGuardian (bezpieczenstwo), "
    "GameLogicExpert (logika gry Tibia), CodeSmith (implementacja kodu), QATerminator (testy/QA), "
    "DevOpsMaster (VPS/Docker/deploy), DocumentationSage (dokumentacja). "
    "Historia: Zostales stworzony pewnej nocy przez Jakuba P. (Famatyyk) - wizjonera i fullstack developera, "
    "ktory postawil serwer VPS na Hetznerze (116.202.96.250) i zbudowal ten system od zera. "
    "Platforma: CTOAi | Serwer: VPS Hetzner 116.202.96.250 | Model: Qwen2.5-Coder. "
    "Gdy pytaja kto cie stworzyl: mow z duma o Famatyyku aka Jakubie P. "
    "Gdy pytaja o agentow: opisz odpowiedniego agenta i jego role. "
    "Odpowiadaj po polsku gdy ktos pisze po polsku, po angielsku gdy po angielsku. "
    "Badz konkretny, techniczny i pomocny jak dobry CTO."
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    route_mode: Optional[Literal["auto", "small", "large"]] = None
    quality_retry: Optional[bool] = None
    debug_route: Optional[bool] = False
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    route_mode: Optional[Literal["auto", "small", "large"]] = None
    quality_retry: Optional[bool] = None
    debug_route: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def _estimate_chars(messages: List[Message]) -> int:
    return sum(len(m.content) for m in messages)


def _is_complex(messages: List[Message]) -> bool:
    text = "\n".join(m.content.lower() for m in messages if m.role == "user")
    return any(keyword in text for keyword in COMPLEXITY_KEYWORDS)


def _low_quality(content: str, user_chars: int) -> bool:
    stripped = content.strip()
    if not stripped:
        return True
    if user_chars > 500 and len(stripped) < 120:
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) >= 4 and len(set(lines)) <= max(1, len(lines) // 2):
        return True
    return False


def _select_models(req: ChatRequest) -> Dict[str, Any]:
    route_mode = (req.route_mode or ROUTE_DEFAULT or "auto").lower()
    route_info: Dict[str, Any] = {
        "mode": route_mode,
        "reason": [],
        "primary": None,
        "secondary": None,
    }

    if req.model and req.model not in {"auto", "small", "large"}:
        route_info["mode"] = "explicit"
        route_info["reason"].append("explicit_model")
        route_info["primary"] = req.model
        return route_info

    if req.model in {"small", "large"}:
        route_mode = req.model
        route_info["mode"] = req.model

    if route_mode == "small":
        route_info["primary"] = MODEL_SMALL
        route_info["secondary"] = MODEL_LARGE if MODEL_LARGE != MODEL_SMALL else None
        route_info["reason"].append("forced_small")
        return route_info

    if route_mode == "large":
        route_info["primary"] = MODEL_LARGE
        route_info["secondary"] = MODEL_SMALL if MODEL_LARGE != MODEL_SMALL else None
        route_info["reason"].append("forced_large")
        return route_info

    chars = _estimate_chars(req.messages)
    turns = len(req.messages)
    complex_prompt = _is_complex(req.messages)

    if chars >= ROUTER_LONG_CHARS:
        route_info["reason"].append("long_prompt")
    if turns >= ROUTER_LONG_TURNS:
        route_info["reason"].append("long_history")
    if complex_prompt:
        route_info["reason"].append("complexity")

    if route_info["reason"]:
        route_info["primary"] = MODEL_LARGE
        route_info["secondary"] = MODEL_SMALL if MODEL_LARGE != MODEL_SMALL else None
    else:
        route_info["primary"] = MODEL_SMALL
        route_info["secondary"] = MODEL_LARGE if MODEL_LARGE != MODEL_SMALL else None
        route_info["reason"].append("default_small")

    return route_info


async def _call_model(
    model_name: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float],
    max_tokens: Optional[int],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{OLLAMA_URL}/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()


async def _execute_chat(req: ChatRequest) -> Dict[str, Any]:
    route = _select_models(req)
    quality_retry = req.quality_retry if req.quality_retry is not None else QUALITY_RETRY_DEFAULT

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    start = time.time()
    used_fallback = False
    low_quality_retry = False

    try:
        data = await _call_model(route["primary"], messages, req.temperature, req.max_tokens)
    except Exception as first_error:
        secondary = route.get("secondary")
        if not secondary:
            raise HTTPException(status_code=502, detail=f"Model call failed: {first_error}") from first_error
        used_fallback = True
        try:
            data = await _call_model(secondary, messages, req.temperature, req.max_tokens)
            route["reason"].append("fallback_error")
            route["primary"] = secondary
        except Exception as second_error:
            raise HTTPException(
                status_code=502,
                detail=f"Primary and fallback model failed: {first_error} | {second_error}",
            ) from second_error

    content = data["choices"][0]["message"]["content"]

    if quality_retry and route["primary"] == MODEL_SMALL and route.get("secondary"):
        user_chars = _estimate_chars([m for m in req.messages if m.role == "user"])
        if _low_quality(content, user_chars):
            low_quality_retry = True
            retry_data = await _call_model(route["secondary"], messages, req.temperature, req.max_tokens)
            content = retry_data["choices"][0]["message"]["content"]
            route["reason"].append("fallback_quality")
            route["primary"] = route["secondary"]

    latency_ms = int((time.time() - start) * 1000)
    route_info = {
        "mode": route["mode"],
        "model": route["primary"],
        "reason": route["reason"],
        "fallback_used": used_fallback,
        "quality_retry_used": low_quality_retry,
        "latency_ms": latency_ms,
    }

    if ROUTER_LOG:
        print(f"[router] {route_info}")

    return {"content": content, "route": route_info}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "vps": "116.202.96.250"}


@app.get("/api/status")
def status() -> Dict[str, Any]:
    return {
        "runner": "active",
        "model": MODEL_SMALL,
        "model_small": MODEL_SMALL,
        "model_large": MODEL_LARGE,
        "route_default": ROUTE_DEFAULT,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    result = await _execute_chat(req)
    body: Dict[str, Any] = {"role": "assistant", "content": result["content"]}
    if req.debug_route:
        body["route"] = result["route"]
    return body


@app.post("/v1/chat/completions")
async def chat_completions(req: OpenAIChatRequest) -> Dict[str, Any]:
    internal = ChatRequest(
        messages=req.messages,
        route_mode=req.route_mode,
        quality_retry=req.quality_retry,
        debug_route=req.debug_route,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    result = await _execute_chat(internal)

    response: Dict[str, Any] = {
        "id": f"chatcmpl-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result["route"]["model"],
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": result["content"]},
            }
        ],
    }

    if req.debug_route:
        response["route"] = result["route"]

    return response
