"""今日小猪的业务实现层。

分层：config / models（值对象）→ storage / repository（数据来源）→
text / renderer（渲染）→ service（用例）→ adapter（AstrBot 边界）。
"""

from __future__ import annotations
