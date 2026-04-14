"""Rule-based query templates for trend discovery."""

from __future__ import annotations

from tide_watch.sources.search.models import SearchMonitorConfig


def apply_template(template_name: str, monitor: SearchMonitorConfig) -> list[tuple[str, str]]:
    topic = monitor.topic
    risk_terms = monitor.risk_terms or ["outage", "lawsuit", "incident", "safety", "ban"]
    competitors = monitor.competitors or []
    products = monitor.products or [topic]

    if template_name == "brand_updates":
        return [(f'"{topic}" (announcement OR update OR roadmap)', "brand_updates")]
    if template_name == "brand_risk":
        joined = " OR ".join(f'"{x}"' for x in risk_terms)
        return [(f'"{topic}" ({joined})', "brand_risk")]
    if template_name == "product_updates":
        out: list[tuple[str, str]] = []
        for p in products:
            out.append((f'"{p}" (release OR changelog OR launch)', "product_updates"))
        return out
    if template_name == "product_feedback":
        out = []
        for p in products:
            out.append((f'"{p}" (review OR complaint OR feedback)', "product_feedback"))
        return out
    if template_name == "competitor_tracking":
        out = []
        for c in competitors:
            out.append((f'"{topic}" "{c}" (benchmark OR compare OR pricing)', "competitor_tracking"))
        return out
    if template_name == "industry_trend":
        return [(f'"{topic}" (trend OR forecast OR adoption)', "industry_trend")]
    return [(f'"{topic}"', "fallback")]
