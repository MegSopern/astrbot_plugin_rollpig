"""今日小猪的业务实现层。

与 AstrBot 框架解耦（仅 ``presenter`` / ``targeting`` 依赖事件与消息组件），
可按「配置 → 存储 → 仓库 → 渲染 → 用例 → 呈现」单独测试与替换。
"""

from __future__ import annotations

from . import messages
from .config import PluginSettings
from .fonts import FontLibrary
from .models import DailyBoard, Pig
from .presenter import PigPresenter
from .renderer import CanvasSpec, PigCardRenderer
from .repository import PigRepository
from .service import RollPigService
from .storage import DailyBoardStore, JsonStore
from .targeting import AtTargetResolver, TargetDecision
from .typography import TextMetrics

__all__ = [
    "AtTargetResolver",
    "CanvasSpec",
    "DailyBoard",
    "DailyBoardStore",
    "FontLibrary",
    "JsonStore",
    "Pig",
    "PigCardRenderer",
    "PigPresenter",
    "PigRepository",
    "PluginSettings",
    "RollPigService",
    "TargetDecision",
    "TextMetrics",
    "messages",
]
