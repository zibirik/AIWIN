from __future__ import annotations

import os
from typing import Optional

import requests


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() else default


def ask_llm_sync(prompt: str) -> str:
    """
    Minimal "AI" integration for unknown phrases.

    Uses OpenAI-compatible chat endpoint:
      POST {base_url}/chat/completions
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return ""

    api_key = _env("JARVIS_OPENAI_API_KEY") or _env("OPENAI_API_KEY")
    base_url = _env("JARVIS_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
    # Ollama (/v1) принимает любой Bearer; часто забывают ключ — подставляем типовой.
    if not api_key and base_url:
        low = base_url.lower()
        if "11434" in low or "ollama" in low:
            api_key = "ollama"
            print("[JARVIS][LLM] No API key; using Ollama placeholder (set JARVIS_OPENAI_API_KEY if needed).", flush=True)
    model = _env("JARVIS_OPENAI_MODEL") or "gpt-3.5-turbo"
    system_prompt = _env(
        "JARVIS_LLM_SYSTEM_PROMPT",
        "Ты ассистент JARVIS. Отвечай по-русски, кратко и по делу. Если вопрос не про команды, ответь на вопрос.",
    )

    if not api_key:
        # Без ключа просто ничего не возвращаем — но это важно для диагностики.
        print("[JARVIS][LLM] No API key set (JARVIS_OPENAI_API_KEY/OPENAI_API_KEY).", flush=True)
        return ""

    url = f"{base_url}/chat/completions"
    print(f"[JARVIS][LLM] POST {url} model={model} prompt_len={len(prompt)}", flush=True)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 400:
            snippet = (resp.text or "")[:200]
            print(f"[JARVIS][LLM] HTTP {resp.status_code}: {snippet}", flush=True)
            return ""
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            print("[JARVIS][LLM] No choices in response.", flush=True)
            return ""
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        print(f"[JARVIS][LLM] Got answer_len={len(content)}", flush=True)
        return str(content).strip()
    except Exception as e:
        print(f"[JARVIS][LLM] Exception: {e}", flush=True)
        return ""

