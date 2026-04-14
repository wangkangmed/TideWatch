"""覆盖评估：CoverageAnalyzer；可 LLM 生成 gap 自然语言描述。"""

from typing import Any

from tide_watch.models.graph_state import TideWatchState


def node_coverage_analyze(state: TideWatchState) -> dict[str, Any]:
    """设置 should_continue_collect / gap_descriptors / coverage_vector。"""
    return {
        "should_continue_collect": False,
        "coverage_vector": {
            "official": 1.0,
            "social": 0.0,
            "search": 0.0,
            "note": "官网 RSS 已跑通（OpenAI / Anthropic / Google AI）；社媒与搜索未启用",
        },
        "gap_descriptors": [],
    }
