"""用户可见文案。

集中管理文案，避免同一句话散落在多处；后续接入 i18n 时只需替换本模块。
"""

from __future__ import annotations

from typing import Final

# 指令交互
MULTI_TARGET_REJECTED: Final[str] = "一次只能抽取一个小猪哦！"
ADMIN_TARGET_REJECTED: Final[str] = "你这只小猪，不许对主人不敬！"
CATALOG_UNAVAILABLE: Final[str] = "小猪信息加载失败，请检查后台报错！"

# 卡片消息
CARD_PREFIX: Final[str] = "这是你的今日小猪："
AT_SEPARATOR: Final[str] = ". "

# 降级消息
FALLBACK_TEMPLATE: Final[str] = (
    "【今日小猪】\n名称：{name}\n描述：{description}\n解析：{analysis}"
)
IMAGE_SEND_FAILED_HINT: Final[str] = "\n\n（图片发送失败，仅展示文字信息）"

# 渲染占位
IMAGE_LOAD_FAILED: Final[str] = "图片加载失败"

# 数据缺省值
UNKNOWN_NAME: Final[str] = "未知小猪"
UNKNOWN_DESCRIPTION: Final[str] = "无描述"
UNKNOWN_ANALYSIS: Final[str] = "无解析"
