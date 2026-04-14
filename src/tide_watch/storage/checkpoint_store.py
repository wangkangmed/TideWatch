"""LangGraph checkpointer 适配：长期运行与恢复。"""

from typing import Protocol

from langgraph.checkpoint.base import BaseCheckpointSaver


class CheckpointStore(Protocol):
    """封装 PostgresSaver / RedisSaver / SqliteSaver 等。"""

    def get_saver(self) -> BaseCheckpointSaver: ...
