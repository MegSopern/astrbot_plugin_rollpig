"""卡片渲染：内容块组合 + 纵向居中布局。

渲染层由两类对象协作完成：

- ``ContentBlock`` 家族：每个块只回答「我有多高、我在指定位置怎么画」；
- ``PigCardRenderer``：只负责按顺序排布、整体居中、落盘。

依赖（仓库、字体、度量、日志、规格）全部由构造函数注入，替换实现无需改动渲染流程。
"""

from __future__ import annotations

import abc
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw

from . import messages
from .models import Pig
from .repository import PigRepository
from .text import FontLibrary, FontType, TextMetrics


@dataclass(frozen=True, slots=True)
class CanvasSpec:
    """卡片规格：画布尺寸、字号、间距与配色。"""

    width: int = 800
    height: int = 800
    background: tuple[int, int, int] = (255, 255, 255)
    avatar_size: int = 280
    avatar_hint_offset: int = 120
    spacing_avatar_name: int = 20
    spacing_name_desc: int = 25
    spacing_desc_analysis: int = 30
    name_font_size: int = 66
    desc_font_size: int = 32
    analysis_font_size: int = 28
    error_font_size: int = 24
    analysis_line_height_factor: float = 1.6
    analysis_width_ratio: float = 0.85
    name_color: tuple[int, int, int] = (0, 0, 0)
    desc_color: tuple[int, int, int] = (85, 85, 85)
    analysis_color: tuple[int, int, int] = (51, 51, 51)
    error_color: tuple[int, int, int] = (255, 0, 0)


def _draw_faux_bold(
    drawer: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: FontType,
    fill: tuple[int, int, int],
) -> None:
    """用四向偏移叠加模拟粗体（字体本身无粗体字重时的兜底方案）。"""
    x, y = position
    for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        drawer.text((x + offset_x, y + offset_y), text, fill=fill, font=font)
    drawer.text((x, y), text, fill=fill, font=font)


class ContentBlock(abc.ABC):
    """卡片内容块：自行测量高度、自行绘制。

    渲染器只依赖 ``layout()`` 返回的总高度做纵向排布，块内部细节对外不可见。
    """

    def __init__(self, gap_before: int = 0) -> None:
        self._gap_before = gap_before
        self._content_height = 0

    @property
    def gap_before(self) -> int:
        """与上一个块之间的间距。"""
        return self._gap_before

    @property
    def content_height(self) -> int:
        """最近一次测量得到的内容高度（不含间距）。"""
        return self._content_height

    def layout(self, width: int) -> int:
        """测量内容并返回「间距 + 内容」总高度。"""
        self._content_height = self.measure(width)
        return self._gap_before + self._content_height

    @abc.abstractmethod
    def measure(self, width: int) -> int:
        """返回内容高度（不含前置间距）。"""

    @abc.abstractmethod
    def draw(
        self,
        canvas: PILImage.Image,
        drawer: ImageDraw.ImageDraw,
        top: int,
        width: int,
    ) -> None:
        """在纵向 ``top`` 处绘制本块内容，横向自行居中。"""


class TextBlock(ContentBlock):
    """单行文本块：高度取字体度量，水平居中；子类可改写 ``_paint``。"""

    def __init__(
        self,
        *,
        text: str,
        font: FontType,
        metrics: TextMetrics,
        gap_before: int,
        color: tuple[int, int, int],
    ) -> None:
        super().__init__(gap_before)
        self._text = text
        self._font = font
        self._metrics = metrics
        self._color = color

    def measure(self, width: int) -> int:
        return self._metrics.measure(self._text, self._font)[1]

    def draw(
        self,
        canvas: PILImage.Image,
        drawer: ImageDraw.ImageDraw,
        top: int,
        width: int,
    ) -> None:
        text_width, _ = self._metrics.measure(self._text, self._font)
        self._paint(drawer, ((width - text_width) // 2, top))

    def _paint(
        self, drawer: ImageDraw.ImageDraw, position: tuple[int, int]
    ) -> None:
        """绘制文本本体，默认单次绘制。"""
        drawer.text(position, self._text, fill=self._color, font=self._font)


class NameBlock(TextBlock):
    """名称块：在单行文本基础上加粗显示。"""

    def _paint(
        self, drawer: ImageDraw.ImageDraw, position: tuple[int, int]
    ) -> None:
        _draw_faux_bold(drawer, position, self._text, self._font, self._color)


class AvatarBlock(ContentBlock):
    """头像块：等比缩放后居中裁剪为正方形；缺图时绘制占位提示。"""

    def __init__(
        self,
        *,
        image_path: Path | None,
        spec: CanvasSpec,
        metrics: TextMetrics,
        error_font: FontType,
        logger,
    ) -> None:
        super().__init__(gap_before=0)
        self._image_path = image_path
        self._spec = spec
        self._metrics = metrics
        self._error_font = error_font
        self._logger = logger
        self._image: PILImage.Image | None = None

    def measure(self, width: int) -> int:
        # 测量阶段顺带完成图片加载与裁剪，绘制阶段直接复用
        self._image = self._load_image()
        return self._spec.avatar_size

    def _load_image(self) -> PILImage.Image | None:
        if self._image_path is None:
            return None
        size = self._spec.avatar_size
        try:
            with PILImage.open(self._image_path) as source:
                source.thumbnail((size, size))
                if source.size == (size, size):
                    return source.copy()
                half = size // 2
                center_x, center_y = source.width // 2, source.height // 2
                return source.crop(
                    (center_x - half, center_y - half, center_x + half, center_y + half)
                )
        except Exception as exc:  # 图片损坏 / 格式不支持
            self._logger.error("加载小猪图片失败：%s", exc)
            return None

    def draw(
        self,
        canvas: PILImage.Image,
        drawer: ImageDraw.ImageDraw,
        top: int,
        width: int,
    ) -> None:
        size = self._spec.avatar_size
        left = (width - size) // 2
        if self._image is not None:
            mask = self._image if self._image.mode == "RGBA" else None
            canvas.paste(self._image, (left, top), mask=mask)
            return

        text = messages.IMAGE_LOAD_FAILED
        text_width, _ = self._metrics.measure(text, self._error_font)
        drawer.text(
            ((width - text_width) // 2, top + self._spec.avatar_hint_offset),
            text,
            fill=self._spec.error_color,
            font=self._error_font,
        )


class AnalysisBlock(ContentBlock):
    """解析块：多行文本逐行居中，行距固定。"""

    def __init__(
        self,
        *,
        lines: list[str],
        font: FontType,
        line_height: int,
        gap_before: int,
        color: tuple[int, int, int],
        metrics: TextMetrics,
    ) -> None:
        super().__init__(gap_before)
        self._lines = lines
        self._font = font
        self._line_height = line_height
        self._color = color
        self._metrics = metrics

    def measure(self, width: int) -> int:
        return len(self._lines) * self._line_height

    def draw(
        self,
        canvas: PILImage.Image,
        drawer: ImageDraw.ImageDraw,
        top: int,
        width: int,
    ) -> None:
        line_top = top
        for line in self._lines:
            line_width, _ = self._metrics.measure(line, self._font)
            drawer.text(
                ((width - line_width) // 2, line_top),
                line,
                fill=self._color,
                font=self._font,
            )
            line_top += self._line_height


class PigCardRenderer:
    """把小猪档案渲染成固定尺寸卡片 PNG。"""

    def __init__(
        self,
        *,
        repository: PigRepository,
        fonts: FontLibrary,
        metrics: TextMetrics,
        spec: CanvasSpec,
        logger,
    ) -> None:
        self._repository = repository
        self._fonts = fonts
        self._metrics = metrics
        self._spec = spec
        self._logger = logger

    def render(self, pig: Pig) -> Path | None:
        """渲染并返回临时文件路径；失败返回 ``None``。"""
        spec = self._spec
        canvas = PILImage.new("RGB", (spec.width, spec.height), spec.background)
        drawer = ImageDraw.Draw(canvas)

        blocks = self._compose_blocks(pig)
        total_height = sum(block.layout(spec.width) for block in blocks)
        top = int((spec.height - total_height) // 2)

        for block in blocks:
            top += block.gap_before
            block.draw(canvas, drawer, top, spec.width)
            top += block.content_height

        return self._save(canvas)

    def _compose_blocks(self, pig: Pig) -> list[ContentBlock]:
        """按展示顺序组装内容块。"""
        spec = self._spec
        regular = self._fonts.regular
        name_font = self._fonts.variant(self._fonts.bold, spec.name_font_size)
        desc_font = self._fonts.variant(regular, spec.desc_font_size)
        analysis_font = self._fonts.variant(regular, spec.analysis_font_size)
        error_font = self._fonts.variant(regular, spec.error_font_size)

        line_height = int(spec.analysis_font_size * spec.analysis_line_height_factor)
        max_line_width = int(spec.width * spec.analysis_width_ratio)

        return [
            AvatarBlock(
                image_path=self._repository.find_image(pig.id),
                spec=spec,
                metrics=self._metrics,
                error_font=error_font,
                logger=self._logger,
            ),
            NameBlock(
                text=pig.name,
                font=name_font,
                metrics=self._metrics,
                gap_before=spec.spacing_avatar_name,
                color=spec.name_color,
            ),
            TextBlock(
                text=pig.description,
                font=desc_font,
                metrics=self._metrics,
                gap_before=spec.spacing_name_desc,
                color=spec.desc_color,
            ),
            AnalysisBlock(
                lines=self._metrics.wrap(pig.analysis, analysis_font, max_line_width),
                font=analysis_font,
                line_height=line_height,
                gap_before=spec.spacing_desc_analysis,
                color=spec.analysis_color,
                metrics=self._metrics,
            ),
        ]

    def _save(self, canvas: PILImage.Image) -> Path | None:
        """写入临时 PNG 文件，由调用方负责清理。"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                path = Path(handle.name)
                canvas.save(path, format="PNG", quality=95)
        except Exception as exc:
            self._logger.error("合成图片失败：%s", exc)
            return None

        self._logger.debug("合成图片成功，临时文件路径：%s", path.absolute())
        if not path.exists():
            self._logger.error("临时文件创建失败：%s", path)
            return None
        return path
