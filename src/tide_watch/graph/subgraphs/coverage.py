from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.coverage import node_coverage_analyze


def _build() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("coverage", node_coverage_analyze)
    g.add_edge(START, "coverage")
    g.add_edge("coverage", END)
    return g


coverage_subgraph = _build()
