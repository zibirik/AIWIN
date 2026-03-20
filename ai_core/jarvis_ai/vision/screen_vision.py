from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytesseract

from ..system.rust_client import RustCoreClient


@dataclass
class OCRBlock:
    text: str
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


class ScreenVision:
    def __init__(self, rust_client: RustCoreClient) -> None:
        self.rust_client = rust_client

    async def _capture_image(self) -> Optional[np.ndarray]:
        png_bytes = await self.rust_client.capture_screen()
        if not png_bytes:
            return None
        img_array = np.frombuffer(png_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    async def capture_and_ocr(self) -> str:
        img = await self._capture_image()
        if img is None:
            return ""
        return pytesseract.image_to_string(img, lang="eng+rus")

    async def ocr_blocks(self) -> List[OCRBlock]:
        """OCR с координатами блоков для экранного читалки и клика по тексту."""
        img = await self._capture_image()
        if img is None:
            return []
        try:
            data = pytesseract.image_to_data(img, lang="eng+rus", output_type=pytesseract.Output.DICT)
        except Exception:
            return []
        blocks: List[OCRBlock] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data.get("text") or [])[i] or ""
            if not text.strip():
                continue
            x = (data.get("left") or [0])[i]
            y = (data.get("top") or [0])[i]
            w = (data.get("width") or [0])[i]
            h = (data.get("height") or [0])[i]
            blocks.append(OCRBlock(text=text.strip(), x=x, y=y, w=w, h=h))
        return blocks

    async def find_click_for_text(self, search_text: str) -> Optional[Tuple[int, int]]:
        """Ищет на экране текст (подстрока) и возвращает координаты центра для клика."""
        if not search_text or not search_text.strip():
            return None
        blocks = await self.ocr_blocks()
        search_lower = search_text.strip().lower()
        for b in blocks:
            if search_lower in b.text.lower():
                return b.center
        for b in blocks:
            if b.text.lower().startswith(search_lower) or search_lower.startswith(b.text.lower()):
                return b.center
        return None
