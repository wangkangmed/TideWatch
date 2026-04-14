from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.backfill import node_plan_backfill


def _build() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("plan_backfill", node_plan_backfill)
    g.add_edge(START, "plan_backfill")
    g.add_edge("plan_backfill", END)
    return g


backfill_subgraph = _build()
