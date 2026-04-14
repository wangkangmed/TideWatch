"""采集子图：并行/串行调度 official / social / search connectors。"""

from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.collect import node_collect_official, node_collect_search, node_collect_social


def _build() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("official", node_collect_official)
    g.add_node("social", node_collect_social)
    g.add_node("search", node_collect_search)
    g.add_edge(START, "official")
    g.add_edge("official", "social")
    g.add_edge("social", "search")
    g.add_edge("search", END)
    return g


collect_subgraph = _build()
