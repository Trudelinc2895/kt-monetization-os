"""backend/api/services/digital_leverage_service.py — Digital Leverage AI service"""
from __future__ import annotations
import httpx
from api.config import settings

SYSTEM_PROMPT = "You are a Digital Leverage Engine. Help users multiply their output without multiplying their time."


async def run_digital_leverage(content: str, context: str = "") -> tuple[str, int]:
    """Returns (result_text, token_count). Uses OpenAI with Ollama fallback."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n{content}".strip() if context else content},
    ]
    if settings.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"model": "gpt-4o-mini", "messages": messages, "max_tokens": 2048},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"], data.get("usage", {}).get("total_tokens", 0)
        except Exception:
            pass
    # Ollama fallback
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_CLIENT_BASE_URL}/api/chat",
                json={"model": settings.OLLAMA_DEFAULT_MODEL, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content", "")
            return text, len(text) // 4
    except Exception as e:
        raise RuntimeError(f"AI unavailable: {e}") from e
