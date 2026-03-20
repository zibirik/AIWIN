from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel

from .event_bus import EventBus, Event, EventType
from .agents import build_default_agents
from .plugins.loader import load_plugins, PluginContext
from . import config as jarvis_config


class TextInputBody(BaseModel):
    text: str


class SpeakBody(BaseModel):
    text: str


class ListenBody(BaseModel):
    duration_sec: float = 5.0


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import asyncio
    cfg = getattr(app.state, "_jarvis_cfg", {})
    bus = getattr(app.state, "_jarvis_bus", None)
    rust_client = getattr(app.state, "_jarvis_rust_client", None)
    voice_task = None
    if bus is not None:
        agents = build_default_agents(bus, rust_client)
        for agent in agents:
            await agent.start()
        if cfg.get("plugins", {}).get("enabled", True):
            paths = cfg.get("plugins", {}).get("paths", ["plugins"])
            load_plugins(paths, PluginContext(app=app, bus=bus))
        voice_cfg = cfg.get("voice", {})
        if voice_cfg.get("enabled", True) and voice_cfg.get("always_listen", True):
            print("[JARVIS] Запуск фонового прослушивания голоса...", flush=True)
            from .speech.always_listen import run_always_listen
            voice_task = asyncio.create_task(
                run_always_listen(
                    bus,
                    chunk_seconds=float(voice_cfg.get("chunk_seconds", 6.0)),
                    tail_seconds=float(voice_cfg.get("tail_seconds", 3.0)),
                    command_extra_seconds=float(voice_cfg.get("command_extra_seconds", 3.0)),
                    asr_model=str(voice_cfg.get("asr_model", "base")),
                    asr_load_timeout_sec=float(voice_cfg.get("asr_load_timeout_sec", 900.0)),
                    ack_tts=bool(voice_cfg.get("ack_tts", False)),
                    greeting=voice_cfg.get("greeting", "Слушаю"),
                    enabled=True,
                    wake_phrases=voice_cfg.get("wake_phrases"),
                )
            )
            app.state._jarvis_voice_task = voice_task
    yield
    if voice_task is not None and not voice_task.done():
        voice_task.cancel()
        try:
            await voice_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    cfg = jarvis_config.load_config()
    app = FastAPI(title="JARVIS AI Core", version="0.1.0", lifespan=_lifespan)
    app.state._jarvis_cfg = cfg
    bus = EventBus()
    app.state._jarvis_bus = bus
    try:
        from .system.rust_client import RustCoreClient
        rust_client = RustCoreClient()
    except Exception:
        rust_client = None
    app.state._jarvis_rust_client = rust_client

    @app.get("/")
    async def root():
        from fastapi.responses import HTMLResponse
        return HTMLResponse("""
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>JARVIS</title></head>
        <body style="font-family:sans-serif;max-width:600px;margin:2rem auto;padding:1rem;">
        <h1>JARVIS</h1>
        <p>Сервер работает. Проверка: <a href="/health">/health</a></p>
        <p><strong>Голос:</strong> скажи «Привет, Джарвис» или «Джарвис» — микрофон слушает каждые 3 сек.</p>
        <p><a href="/api/voice/test">Проверить озвучку</a> — используется PowerShell (System.Speech) или pyttsx3. Проверь громкость и устройство вывода в Windows.</p>
        <p>API: POST /api/input/text (body: {"text": "Открой блокнот"}), POST /api/voice/speak (озвучка).</p>
        </body></html>
        """)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        from fastapi.responses import Response
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/input/text")
    async def api_text_input(body: TextInputBody) -> dict:
        await bus.publish(Event.new(type=EventType.TEXT_INPUT, source="api", payload={"text": body.text}))
        return {"ok": True}

    @app.get("/api/status")
    async def api_status() -> dict:
        if rust_client is None:
            raise HTTPException(503, "Rust core not available")
        s = await rust_client.get_system_status()
        return {"cpu_usage": getattr(s, "cpu_usage", 0), "memory_usage": getattr(s, "memory_usage", 0), "battery_level": getattr(s, "battery_level", 0)}

    @app.get("/api/screen/ocr")
    async def api_screen_ocr() -> dict:
        if rust_client is None:
            raise HTTPException(503, "Rust core not available")
        try:
            from .vision.screen_vision import ScreenVision
            vision = ScreenVision(rust_client)
            text = await vision.capture_and_ocr()
            return {"text": text}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/api/voice/listen")
    async def api_voice_listen(body: ListenBody | None = None) -> dict:
        try:
            from .speech.pipeline import VoicePipeline
            duration = body.duration_sec if body else 5.0
            pipeline = VoicePipeline(bus, listen_seconds=duration)
            text = await pipeline.run_once_from_mic(duration_sec=duration)
            return {"text": text or "", "wake_word_detected": bool(text and "джарвис" in (text or "").lower())}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/api/voice/speak")
    async def api_voice_speak(body: SpeakBody) -> dict:
        try:
            from .speech.tts import TTS
            tts = TTS()
            await tts.speak(body.text)
            return {"ok": True}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/voice/test")
    async def api_voice_test():
        """Проверка озвучки (через Windows SAPI, без конфликта с pyttsx3)."""
        import traceback
        from fastapi.responses import HTMLResponse
        from html import escape
        try:
            from .speech.tts import TTS
            tts = TTS()
            if not tts._ensure_engine():
                return HTMLResponse(
                    "<html><body><h1>Ошибка</h1><p>TTS недоступен (нужен Windows SAPI или pyttsx3).</p><a href='/'>Назад</a></body></html>",
                    status_code=200,
                )
            await tts.speak("Проверка звука. Если вы это слышите, озвучка работает.")
            return HTMLResponse("<html><body><h1>Озвучка работает</h1><p>Должны были услышать фразу.</p><a href='/'>Назад</a></body></html>")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[JARVIS] Ошибка /api/voice/test: {e}\n{tb}", flush=True)
            err_msg = escape(str(e))
            tb_esc = escape(tb)
            return HTMLResponse(
                f"<html><body><h1>Ошибка TTS</h1><pre>{err_msg}</pre><details><summary>Подробнее</summary><pre>{tb_esc}</pre></details><a href='/'>Назад</a></body></html>",
                status_code=200,
            )

    return app


def run_app(app: FastAPI) -> None:
    cfg = getattr(app.state, "_jarvis_cfg", {}) or jarvis_config.load_config()
    host = cfg.get("app", {}).get("http_host", "127.0.0.1")
    port = cfg.get("app", {}).get("http_port", 8000)
    uvicorn.run(app, host=str(host), port=int(port))

