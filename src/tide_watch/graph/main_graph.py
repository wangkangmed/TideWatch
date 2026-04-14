"""Five-layer main graph: Sources -> Evidence -> Events -> Intelligence -> Decision Support."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from tide_watch.models.graph_state import TideWatchState
from tide_watch.nodes.collect import run_sources
from tide_watch.nodes.decision_support import run_decision_support
from tide_watch.nodes.events import run_events
from tide_watch.nodes.intelligence import run_intelligence
from tide_watch.nodes.normalize import build_evidence


def build_main_graph() -> StateGraph:
    g = StateGraph(TideWatchState)
    g.add_node("run_sources", run_sources)
    g.add_node("build_evidence", build_evidence)
    g.add_node("run_events", run_events)
    g.add_node("run_intelligence", run_intelligence)
    g.add_node("run_decision_support", run_decision_support)

    g.add_edge(START, "run_sources")
    g.add_edge("run_sources", "build_evidence")
    g.add_edge("build_evidence", "run_events")
    g.add_edge("run_events", "run_intelligence")
    g.add_edge("run_intelligence", "run_decision_support")
    g.add_edge("run_decision_support", END)
    return g


def compile_app():
    return build_main_graph().compile()
