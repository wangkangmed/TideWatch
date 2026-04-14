"""补采规划：BackfillPlanner；允许 LLM 将 gap 转为可执行检索参数。"""

from typing import Any

from tide_watch.models.graph_state import TideWatchState


def node_plan_backfill(state: TideWatchState) -> dict[str, Any]:
    """产出 backfill_requests，并递增 collect_round（或由主图 reducer 处理）。"""
    return {"collect_round": (state.get("collect_round") or 0) + 1}
