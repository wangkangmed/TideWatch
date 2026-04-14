"""采集幂等：已见 idempotency_key 跳过或更新策略。"""

from typing import Protocol


class IdempotencyStore(Protocol):
    def seen(self, key: str) -> bool: ...
    def mark(self, key: str) -> None: ...
