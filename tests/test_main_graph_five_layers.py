from __future__ import annotations

from tide_watch.graph.main_graph import build_main_graph, compile_app


def test_main_graph_invoke_runs_five_layers(monkeypatch):
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.run_sources",
        lambda _state: {
            "raw_batches": [],
            "source_errors": [],
            "source_metadata": {"official": {}, "social": {}, "search": {}},
        },
    )
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.build_evidence",
        lambda _state: {"normalized_docs": [], "evidence_items": []},
    )
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.run_events",
        lambda _state: {"events": [], "event_evidence_links": []},
    )
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.run_intelligence",
        lambda _state: {"trends": [], "findings": [], "alerts": [], "briefing_items": []},
    )
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.run_decision_support",
        lambda _state: {"decision_signals": [], "recommendation_items": [], "decision_briefs": []},
    )
    monkeypatch.setattr(
        "tide_watch.graph.main_graph.persist_pipeline_results",
        lambda _state: {},
    )
    app = compile_app()
    out = app.invoke(
        {"run_id": "r1", "scope": {}},
        config={"configurable": {"thread_id": "test_five_layers"}},
    )
    assert "decision_briefs" in out


def test_main_graph_mermaid_contains_all_nodes():
    from langgraph.checkpoint.memory import MemorySaver

    graph = build_main_graph().compile(checkpointer=MemorySaver()).get_graph()
    mermaid = graph.draw_mermaid()
    for node_name in (
        "run_sources",
        "build_evidence",
        "run_events",
        "run_intelligence",
        "run_decision_support",
        "persist_results",
    ):
        assert node_name in mermaid


def test_sources_layer_aggregates_official_social_search(monkeypatch):
    from tide_watch.nodes.collect import run_sources

    async def _official(_state):
        return {"raw_batches": [], "source_metadata": {"official_candidates": 1}}

    async def _social(_state):
        return {"raw_batches": [], "source_metadata": {"social_batches": 1}}

    async def _search(_state):
        return {"raw_batches": [], "source_metadata": {"search_ranked": 1}}

    monkeypatch.setattr(
        "tide_watch.nodes.collect.node_collect_official",
        _official,
    )
    monkeypatch.setattr(
        "tide_watch.nodes.collect.node_collect_social",
        _social,
    )
    monkeypatch.setattr(
        "tide_watch.nodes.collect.node_collect_search",
        _search,
    )
    out = run_sources({"scope": {}})
    assert "official" in out["source_metadata"]
    assert "social" in out["source_metadata"]
    assert "search" in out["source_metadata"]


def test_official_html_capability_adapter_is_invoked(monkeypatch):
    from tide_watch.nodes.collect import node_collect_official

    class _C:
        def __init__(self, source_id: str, url: str):
            self.source_id = source_id
            self.url = url
            self.company = "OpenAI"
            self.metadata = {"transport": "html_listing"}
            self.hint_doc_type = "listing"

    monkeypatch.setattr("tide_watch.nodes.collect.load_source_config", lambda _p: object())
    monkeypatch.setattr("tide_watch.nodes.collect.collect_official_discovery", lambda *a, **k: [_C("s1", "https://a.com/news")])
    monkeypatch.setattr(
        "tide_watch.nodes.collect.apply_official_html_capability",
        lambda candidates, **kwargs: list(candidates) + [_C("s1", "https://a.com/news/item-1")],
    )
    import asyncio

    out = asyncio.run(node_collect_official({"scope": {}}))
    assert out["source_metadata"]["official_html_capability"] is True
    assert out["source_metadata"]["official_candidates"] == 2
