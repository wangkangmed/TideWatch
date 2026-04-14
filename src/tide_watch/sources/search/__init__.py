"""Search discovery module: external discovery + candidate generation."""

from tide_watch.sources.search.config_loader import load_search_registry
from tide_watch.sources.search.pipeline import run_search_discovery, run_search_discovery_with_fetch_plans

__all__ = ["load_search_registry", "run_search_discovery", "run_search_discovery_with_fetch_plans"]
