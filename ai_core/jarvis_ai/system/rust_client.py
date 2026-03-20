from __future__ import annotations

from typing import Any

from .. import config as jarvis_config

try:
    import grpc
    from jarvis_ai.proto import system_control_pb2 as pb2
    from jarvis_ai.proto import system_control_pb2_grpc as pb2_grpc
    _HAS_GRPC = True
except ImportError:
    _HAS_GRPC = False
    pb2 = None
    pb2_grpc = None


def _load_config() -> dict:
    return jarvis_config.load_config()


class RustCoreClient:
    def __init__(self) -> None:
        cfg = _load_config()
        self._addr = cfg.get("rust_core", {}).get("grpc_address", "127.0.0.1:50051")
        self._auth_token = cfg.get("rust_core", {}).get("auth_token", "")
        self._channel = None
        self._stub = None
        if _HAS_GRPC and pb2 is not None and pb2_grpc is not None:
            self._channel = grpc.aio.insecure_channel(self._addr)
            self._stub = pb2_grpc.SystemControlServiceStub(self._channel)

    def _auth(self) -> Any:
        if pb2 is None:
            return None
        return pb2.AuthToken(token=self._auth_token)

    async def get_system_status(self) -> Any:
        if self._stub is None:
            return type("R", (), {"cpu_usage": 0.0, "memory_usage": 0.0, "battery_level": 0.0})()
        req = pb2.GetSystemStatusRequest(auth=self._auth())
        return await self._stub.GetSystemStatus(req)

    async def launch_application(self, path: str, args: list[str] | None = None, working_dir: str = "") -> Any:
        if self._stub is None:
            return type("R", (), {"success": False, "error_message": "gRPC stubs not generated"})()
        req = pb2.LaunchApplicationRequest(auth=self._auth(), path=path, args=args or [], working_dir=working_dir or "")
        return await self._stub.LaunchApplication(req)

    async def capture_screen(self) -> bytes:
        if self._stub is None:
            return b""
        req = pb2.CaptureScreenRequest(auth=self._auth())
        resp = await self._stub.CaptureScreen(req)
        return getattr(resp, "image_png", b"")

    async def type_text(self, text: str) -> Any:
        if self._stub is None:
            return
        req = getattr(pb2, "SimulateKeyRequest", None)
        if req is None:
            return
        await self._stub.SimulateKey(req(auth=self._auth(), text=text))

    async def move_mouse(self, x: int, y: int) -> Any:
        if self._stub is None:
            return
        req = getattr(pb2, "MoveMouseRequest", None)
        if req is None:
            return
        await self._stub.MoveMouse(req(auth=self._auth(), x=x, y=y))

    async def click_mouse(self, x: int = 0, y: int = 0, button: str = "left") -> Any:
        if self._stub is None:
            return
        req = getattr(pb2, "ClickMouseRequest", None)
        if req is None:
            return
        await self._stub.ClickMouse(req(auth=self._auth(), x=x, y=y, button=button))

    async def read_clipboard(self) -> str:
        if self._stub is None:
            return ""
        req = getattr(pb2, "ReadClipboardRequest", None)
        if req is None:
            return ""
        resp = await self._stub.ReadClipboard(req(auth=self._auth()))
        return getattr(resp, "text", "") or ""

    async def set_clipboard(self, text: str) -> Any:
        if self._stub is None:
            return
        req = getattr(pb2, "SetClipboardRequest", None)
        if req is None:
            return
        await self._stub.SetClipboard(req(auth=self._auth(), text=text))
