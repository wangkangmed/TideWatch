from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.normalize import node_normalize_batch


def _build() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("normalize", node_normalize_batch)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", END)
    return g


normalize_subgraph = _build()
