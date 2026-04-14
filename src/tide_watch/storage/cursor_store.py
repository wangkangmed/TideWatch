"""Provider 游标持久化：与图 checkpoint 分离时可单独存储。"""

from typing import Any, Protocol


class PerProviderCursorStore(Protocol):
    def load(self, run_id: str, provider_id: str) -> dict[str, Any] | None: ...
    def save(self, run_id: str, provider_id: str, blob: dict[str, Any]) -> None: ...
