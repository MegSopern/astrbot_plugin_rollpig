"""文字度量：尺寸测量与按宽度折行。"""

from __future__ import annotations

from PIL import Image as PILImage
from PIL import ImageDraw

from .fonts import FontType


class TextMetrics:
    """复用同一块 1x1 画布测量文字，避免每次测量都新建图像。"""

    def __init__(self) -> None:
        self._scratch_image = PILImage.new("RGB", (1, 1))
        self._drawer = ImageDraw.Draw(self._scratch_image)

    def measure(self, text: str, font: FontType) -> tuple[int, int]:
        """返回文字宽高；Pillow < 8 无 ``textbbox`` 时回退 ``textsize``。"""
        try:
            left, top, right, bottom = self._drawer.textbbox((0, 0), text, font=font)
        except AttributeError:
            return self._drawer.textsize(text, font=font)
        return right - left, bottom - top

    def wrap(self, text: str, font: FontType, max_width: int) -> list[str]:
        """按像素宽度逐字折行，返回每行文本。"""
        lines: list[str] = []
        current = ""
        for char in text:
            current += char
            width, _ = self.measure(current, font)
            if width > max_width:
                lines.append(current[:-1])
                current = char
        if current:
            lines.append(current)
        return lines
