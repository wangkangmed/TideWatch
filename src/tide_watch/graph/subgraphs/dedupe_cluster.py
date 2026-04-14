from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.dedupe_cluster import node_dedupe_cluster


def _build() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("dedupe_cluster", node_dedupe_cluster)
    g.add_edge(START, "dedupe_cluster")
    g.add_edge("dedupe_cluster", END)
    return g


dedupe_cluster_subgraph = _build()
