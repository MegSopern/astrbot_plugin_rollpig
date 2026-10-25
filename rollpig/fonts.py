"""字体加载：模板方法基类 + 声明式子类。

分层要点：
- ``FontLoader`` 固定「按候选顺序尝试 → 逐个降级 → 兜底默认字体」的流程；
- 子类只用类属性声明用途、字号与候选文件，不重复流程代码；
- ``FontLibrary`` 作为门面，向渲染层暴露常规字体、加粗字体与字号变体。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar

from PIL import ImageFont

FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont


class FontLoader:
    """字体加载模板。

    子类必须声明 ``purpose``、``size`` 与至少一组候选文件；``candidates``
    先解析插件内字体目录，再回退到系统字体路径。
    """

    purpose: ClassVar[str]
    size: ClassVar[int]
    local_candidates: ClassVar[tuple[str, ...]] = ()
    system_candidates: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        missing = [
            name for name in ("purpose", "size") if getattr(cls, name, None) is None
        ]
        if missing:
            raise TypeError(f"{cls.__name__} 未声明类属性：{', '.join(missing)}")

    def __init__(self, font_dir: Path, logger: logging.Logger) -> None:
        self._font_dir = font_dir
        self._logger = logger

    @property
    def candidates(self) -> tuple[Path, ...]:
        """按优先级排列的候选字体路径。"""
        local = tuple(self._font_dir / name for name in self.local_candidates)
        return local + tuple(Path(path) for path in self.system_candidates)

    def load(self) -> FontType:
        """加载首个可用字体，全部失败时返回 PIL 默认字体。"""
        for path in self.candidates:
            if not path.exists():
                continue
            try:
                return ImageFont.truetype(str(path), self.size)
            except Exception as exc:  # 字体文件损坏 / 平台不支持
                self._logger.warning("加载%s字体%s失败：%s", self.purpose, path, exc)
        self._logger.warning("未找到%s字体，使用默认字体", self.purpose)
        return ImageFont.load_default()


class RegularFontLoader(FontLoader):
    """常规字体：描述与解析正文。"""

    purpose = "常规"
    size = 32
    local_candidates = ("可爱字体.ttf", "SourceHanSansCN-Regular.otf")
    system_candidates = (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/PingFang.ttc",
    )


class BoldFontLoader(FontLoader):
    """加粗字体：小猪名称。"""

    purpose = "加粗"
    size = 66
    local_candidates = ("荆南麦圆体.otf", "SourceHanSansCN-Bold.otf")
    system_candidates = (
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/PingFang.ttc",
    )


class FontLibrary:
    """字体库门面：持有本次加载的常规 / 加粗字体。"""

    def __init__(self, font_dir: Path, logger: logging.Logger) -> None:
        self._logger = logger
        self.regular = RegularFontLoader(font_dir, logger).load()
        self.bold = BoldFontLoader(font_dir, logger).load()

    def variant(self, base: FontType, size: int) -> FontType:
        """取同一字体的指定字号版本；不支持变体时返回原字体。"""
        try:
            return base.font_variant(size=size)
        except AttributeError:
            self._logger.warning("当前字体不支持字号变体，沿用原字号")
            return base
