"""运行时上下文、会话状态和长期记忆的分层管理。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class ContextManager:
    """教学版长期记忆存储，按用户命名空间隔离。"""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = defaultdict(dict)

    def remember(self, user_id: str, key: str, value: Any) -> None:
        self._store[user_id][key] = value

    def recall(self, user_id: str, key: str) -> Any | None:
        return self._store.get(user_id, {}).get(key)

    def forget(self, user_id: str, key: str) -> bool:
        values = self._store.get(user_id, {})
        if key not in values:
            return False
        del values[key]
        return True

    @staticmethod
    def trim_messages(messages: list[dict[str, str]], keep: int = 12) -> list[dict[str, str]]:
        """保留系统提示和最近消息，限制上下文无限增长。"""
        system = [message for message in messages if message.get("role") == "system"][:1]
        dialogue = [message for message in messages if message.get("role") != "system"][-keep:]
        return system + dialogue

