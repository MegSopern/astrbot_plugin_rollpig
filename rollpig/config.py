"""插件配置的不可变值对象。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class PluginSettings:
    """插件运行期所需配置（构造后不可变，便于跨协程共享）。

    由 ``_conf_schema.json`` 的配置字典与全局管理员列表装配，业务层只依赖本对象，
    不再直接读取裸 dict。
    """

    at_view_pig: bool = False
    at_reply_user: bool = True
    wake_free_trigger: bool = False
    admin_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(
        cls,
        config: Mapping[str, Any],
        admin_ids: Iterable[Any] = (),
    ) -> PluginSettings:
        """由插件配置字典构造配置对象。"""
        return cls(
            at_view_pig=bool(config.get("at_view_pig", False)),
            at_reply_user=bool(config.get("at_reply_user", True)),
            wake_free_trigger=bool(config.get("wake_free_trigger", False)),
            admin_ids=tuple(str(item) for item in admin_ids),
        )

    def is_admin(self, user_id: str) -> bool:
        """判断用户是否属于全局管理员。"""
        return user_id in self.admin_ids
