"""Intelligence layer node: merge event stories and route findings heuristically."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

from tide_watch.models.graph_state import TideWatchState
from tide_watch.models.normalized import NormalizedDocument
from tide_watch.models.pipeline import (
    AlertItem,
    BriefingItem,
    EventItem,
    EvidenceItem,
    Finding,
    TrendSignal,
)

_GENERIC_SUBJECTS = {
    "",
    "http",
    "https",
    "www",
    "com",
    "org",
    "net",
    "news",
    "blog",
    "docs",
    "doc",
    "release",
    "releases",
    "notes",
    "overview",
    "article",
    "post",
    "log",
    "update",
    "updates",
    "research",
}
_TOKEN_STOPWORDS = _GENERIC_SUBJECTS | {
    "ai",
    "for",
    "the",
    "and",
    "with",
    "from",
    "into",
    "across",
    "about",
    "over",
    "under",
    "this",
    "that",
    "their",
    "its",
    "new",
}
_RISK_KEYWORDS = {
    "outage",
    "incident",
    "breach",
    "lawsuit",
    "ban",
    "fine",
    "regulation",
    "regulatory",
    "security",
    "safety",
    "privacy",
    "recall",
    "vulnerability",
    "cve",
    "investigation",
}
_OPPORTUNITY_KEYWORDS = {
    "funding",
    "partnership",
    "partner",
    "deal",
    "acquisition",
    "invest",
    "investment",
    "raised",
    "expansion",
    "win",
}
_ADOPTION_KEYWORDS = {
    "launch",
    "launched",
    "release",
    "released",
    "rollout",
    "rolls",
    "adoption",
    "integrat",
    "deploy",
    "usage",
    "preview",
    "changelog",
}
_COMPETITION_KEYWORDS = {
    "benchmark",
    "benchmarks",
    "leaderboard",
    "compare",
    "comparison",
    "competitor",
    "competition",
    "versus",
    "vs",
    "race",
    "outperform",
    "market-share",
}
_ENTITY_ALIASES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepmind": "Google DeepMind",
    "google": "Google",
    "meta": "Meta",
    "facebook": "Meta",
    "microsoft": "Microsoft",
    "nvidia": "NVIDIA",
    "xai": "xAI",
    "mistral": "Mistral",
    "cohere": "Cohere",
    "huggingface": "Hugging Face",
    "hf": "Hugging Face",
}
_EVENT_LABELS = {
    "risk_event": "risk event",
    "opportunity_event": "opportunity signal",
    "competition_event": "competition signal",
    "adoption_event": "adoption signal",
    "research_publication": "narrative signal",
    "story_event": "story signal",
}
_TREND_LABELS = {
    "risk_cluster": "risk cluster",
    "opportunity_cluster": "opportunity cluster",
    "competition_cluster": "competition cluster",
    "adoption_cluster": "adoption cluster",
    "momentum_cluster": "momentum cluster",
    "narrative_cluster": "narrative cluster",
}
_FINDING_LABELS = {
    "risk_signal": "Risk signal",
    "opportunity_signal": "Opportunity signal",
    "competition_signal": "Competition signal",
    "adoption_signal": "Adoption signal",
    "narrative_shift": "Narrative shift",
    "momentum_signal": "Momentum signal",
}
_FINDING_ACTIONS = {
    "risk_signal": [
        "Validate the downstream risk and affected stakeholders.",
        "Monitor primary sources for escalation or remediation updates.",
        "Prepare a concise risk brief if significance increases.",
    ],
    "opportunity_signal": [
        "Assess whether this creates a near-term partnership or GTM opportunity.",
        "Track follow-on announcements and customer uptake signals.",
        "Add the story to the next leadership brief if corroboration improves.",
    ],
    "competition_signal": [
        "Compare the move against peer offerings and recent launches.",
        "Watch for competitor responses or follow-up benchmark claims.",
        "Corroborate with at least one additional independent source.",
    ],
    "adoption_signal": [
        "Monitor rollout and customer adoption evidence over the next cycle.",
        "Track product readiness, availability, and follow-up implementation signals.",
        "Brief stakeholders if adoption expands across multiple trusted sources.",
    ],
    "narrative_shift": [
        "Watch for narrative shifts in upcoming coverage.",
        "Review supporting evidence links in the evidence package.",
        "Validate timeline and primary sources before executive comms.",
    ],
    "momentum_signal": [
        "Increase monitoring cadence for this story cluster.",
        "Look for follow-on events that confirm sustained momentum.",
        "Add the cluster to the watch brief if corroboration continues to rise.",
    ],
}


@dataclass
class EventProfile:
    event_id: str
    title: str
    display_title: str
    summary: str
    event_type: str
    event_family: str
    subject: str
    subject_key: str
    source_ids: list[str]
    evidence_ids: list[str]
    doc_ids: list[str]
    canonical_urls: list[str]
    title_tokens: set[str]
    similarity_text: str
    day_bucket: str | None
    event_time: datetime | None
    significance_score: float
    confidence: float
    watchlist_hits: list[str]
    topic_hits: list[str]
    risk_keyword_hits: list[str]
    opportunity_keyword_hits: list[str]
    metadata: dict[str, Any]


def _evt_field(evt: EventItem | dict, field: str, default: Any = None) -> Any:
    if isinstance(evt, dict):
        return evt.get(field, default)
    return getattr(evt, field, default)


def _doc_field(doc: NormalizedDocument | dict, field: str, default: Any = None) -> Any:
    if isinstance(doc, dict):
        return doc.get(field, default)
    return getattr(doc, field, default)


def _evi_field(evi: EvidenceItem | dict, field: str, default: Any = None) -> Any:
    if isinstance(evi, dict):
        return evi.get(field, default)
    return getattr(evi, field, default)


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _unique(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value is None or value == "" or value == []:
            continue
        try:
            if value in seen:
                continue
            seen.add(value)
        except TypeError:
            if value in out:
                continue
        out.append(value)
    return out


def _tokenize(text: str) -> set[str]:
    normalized = (text or "").replace("://", " ").replace("/", " ").replace("_", " ").replace("-", " ")
    tokens = {tok for tok in re.findall(r"[a-z0-9]+", normalized.lower()) if tok and tok not in _TOKEN_STOPWORDS}
    return tokens


def _text_similarity(left: str, right: str) -> float:
    lnorm = _normalize_space(left).lower()
    rnorm = _normalize_space(right).lower()
    if not lnorm or not rnorm:
        return 0.0
    token_left = _tokenize(lnorm)
    token_right = _tokenize(rnorm)
    token_score = 0.0
    if token_left and token_right:
        token_score = len(token_left & token_right) / max(len(token_left | token_right), 1)
    seq_score = SequenceMatcher(None, lnorm, rnorm).ratio()
    return max(token_score, seq_score * 0.8)


def _hash_id(prefix: str, values: list[str]) -> str:
    basis = "|".join(sorted(values))
    return f"{prefix}_{hashlib.sha256(basis.encode()).hexdigest()[:10]}"


def _is_url_like(text: str) -> bool:
    text = (text or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def _extract_keywords(text: str, keywords: set[str]) -> list[str]:
    lowered = (text or "").lower()
    hits = []
    for keyword in sorted(keywords):
        if keyword in lowered:
            hits.append(keyword)
    return hits


def _normalize_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    cleaned = _normalize_space(subject)
    if not cleaned:
        return None
    if cleaned.lower() in _GENERIC_SUBJECTS:
        return None
    if cleaned.lower() in _ENTITY_ALIASES:
        return _ENTITY_ALIASES[cleaned.lower()]
    return cleaned


def _subject_from_source_id(source_id: str | None) -> str | None:
    if not source_id:
        return None
    raw_tokens = [tok for tok in source_id.lower().split("_") if tok]
    generic = {
        "news",
        "blog",
        "docs",
        "doc",
        "release",
        "releases",
        "notes",
        "note",
        "research",
        "product",
        "official",
        "company",
        "technical",
        "engineering",
        "ai",
        "top",
        "feed",
        "search",
        "newsroom",
        "changelog",
    }
    meaningful = [tok for tok in raw_tokens if tok not in generic]
    if not meaningful:
        meaningful = raw_tokens[:2]
    if not meaningful:
        return None
    joined = " ".join(meaningful[:2])
    if joined in _ENTITY_ALIASES:
        return _ENTITY_ALIASES[joined]
    for token in meaningful:
        if token in _ENTITY_ALIASES:
            return _ENTITY_ALIASES[token]
    return " ".join(tok.upper() if len(tok) <= 3 else tok.title() for tok in meaningful[:2])


def _subject_from_urls(urls: list[str]) -> str | None:
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        for key, label in _ENTITY_ALIASES.items():
            if key in host:
                return label
    return None


def _title_from_docs(docs: list[NormalizedDocument | dict]) -> str | None:
    for doc in docs:
        title = _doc_field(doc, "title")
        if title and not _is_url_like(title):
            return _normalize_space(title)
    for doc in docs:
        url = _doc_field(doc, "canonical_url")
        if url:
            return _normalize_space(url)
    return None


def _infer_event_type(title: str, source_ids: list[str], canonical_urls: list[str], docs: list[NormalizedDocument | dict]) -> str:
    text = " ".join([title] + source_ids + canonical_urls + [_title_from_docs(docs) or ""]).lower()
    if any(keyword in text for keyword in _RISK_KEYWORDS):
        return "risk_event"
    if any(keyword in text for keyword in _OPPORTUNITY_KEYWORDS):
        return "opportunity_event"
    if any(keyword in text for keyword in _COMPETITION_KEYWORDS):
        return "competition_event"
    if any(keyword in text for keyword in _ADOPTION_KEYWORDS):
        return "adoption_event"
    if any(token in text for token in ("research", "paper", "benchmark", "analysis")):
        return "research_publication"
    return "story_event"


def _event_family(event_type: str) -> str:
    lowered = (event_type or "").lower()
    if "risk" in lowered or lowered in {"incident", "outage", "regulatory_event"}:
        return "risk"
    if "opportunity" in lowered or lowered in {"funding_event", "partnership_event"}:
        return "opportunity"
    if "competition" in lowered or lowered in {"benchmark_event", "market_move"}:
        return "competition"
    if "adoption" in lowered or lowered in {"product_launch", "release", "rollout"}:
        return "adoption"
    if "research" in lowered or "narrative" in lowered or lowered in {"analysis_event", "media_coverage"}:
        return "narrative"
    return "story"


def _infer_subject(
    explicit_subject: str | None,
    title: str,
    source_ids: list[str],
    canonical_urls: list[str],
    docs: list[NormalizedDocument | dict],
) -> str:
    normalized_subject = _normalize_subject(explicit_subject)
    if normalized_subject:
        return normalized_subject
    for source_id in source_ids:
        subject = _subject_from_source_id(source_id)
        if subject:
            return subject
    subject = _subject_from_urls(canonical_urls)
    if subject:
        return subject
    for doc in docs:
        raw_metadata = _doc_field(doc, "raw_metadata", {}) or {}
        company = raw_metadata.get("company")
        if company:
            return str(company)
    tokens = [tok for tok in re.findall(r"[A-Za-z0-9]+", title or "") if tok.lower() not in _GENERIC_SUBJECTS]
    if tokens:
        candidate = " ".join(tokens[:3])
        return candidate.strip()
    return "Market signal"


def _build_evidence_map(evidence_items: list[EvidenceItem | dict]) -> dict[str, EvidenceItem | dict]:
    evidence_map: dict[str, EvidenceItem | dict] = {}
    for item in evidence_items:
        evidence_id = _evi_field(item, "evidence_id")
        if evidence_id:
            evidence_map[evidence_id] = item
    return evidence_map


def _build_doc_map(docs: list[NormalizedDocument | dict]) -> dict[str, NormalizedDocument | dict]:
    doc_map: dict[str, NormalizedDocument | dict] = {}
    for doc in docs:
        doc_id = _doc_field(doc, "doc_id")
        if doc_id:
            doc_map[doc_id] = doc
    return doc_map


def _build_event_profiles(state: TideWatchState) -> list[EventProfile]:
    evidence_map = _build_evidence_map(state.get("evidence_items") or [])
    doc_map = _build_doc_map(state.get("normalized_docs") or [])
    profiles: list[EventProfile] = []

    for event in state.get("events") or []:
        event_id = str(_evt_field(event, "event_id", "") or "")
        evidence_ids = _unique(list(_evt_field(event, "supporting_evidence_ids") or []))
        docs = []
        doc_ids: list[str] = []
        source_ids = _unique([str(_evt_field(event, "source_id", "") or "")])
        for evidence_id in evidence_ids:
            evidence = evidence_map.get(evidence_id)
            if evidence is None:
                continue
            doc_id = _evi_field(evidence, "doc_id", "")
            if doc_id:
                doc_ids.append(doc_id)
                if doc_id in doc_map:
                    docs.append(doc_map[doc_id])
            source_ids.append(str(_evi_field(evidence, "source_id", "") or ""))
        doc_ids = _unique(doc_ids)
        source_ids = _unique(source_ids)
        canonical_urls = _unique([str(_doc_field(doc, "canonical_url", "") or "") for doc in docs])
        metadata = dict(_evt_field(event, "metadata", {}) or {})
        event_time = _parse_dt(_evt_field(event, "event_time")) or next(
            (
                _parse_dt(_doc_field(doc, "published_at")) or _parse_dt(_doc_field(doc, "updated_at"))
                for doc in docs
                if _parse_dt(_doc_field(doc, "published_at")) or _parse_dt(_doc_field(doc, "updated_at"))
            ),
            None,
        )
        raw_title = (
            _evt_field(event, "canonical_title")
            or _evt_field(event, "title")
            or _title_from_docs(docs)
            or event_id
        )
        raw_title = _normalize_space(str(raw_title))
        summary = _normalize_space(
            str(
                metadata.get("summary")
                or metadata.get("headline")
                or _title_from_docs(docs)
                or raw_title
            )
        )
        event_type = str(_evt_field(event, "event_type") or _infer_event_type(raw_title, source_ids, canonical_urls, docs))
        subject = _infer_subject(_evt_field(event, "subject"), raw_title, source_ids, canonical_urls, docs)
        subject_key = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
        title_tokens = _tokenize(f"{raw_title} {summary}")
        watchlist_hits = _unique(
            list(metadata.get("watchlist_hits") or [])
            + list(metadata.get("watchlist_entity_hits") or [])
        )
        topic_hits = _unique(
            list(metadata.get("topic_hits") or [])
            + list(metadata.get("watchlist_topic_hits") or [])
        )
        risk_keyword_hits = _unique(
            list(metadata.get("risk_keyword_hits") or [])
            + list(metadata.get("watchlist_risk_kw") or [])
            + _extract_keywords(f"{raw_title} {summary}", _RISK_KEYWORDS)
        )
        opportunity_keyword_hits = _unique(
            list(metadata.get("opportunity_keyword_hits") or [])
            + list(metadata.get("watchlist_opportunity_kw") or [])
            + _extract_keywords(f"{raw_title} {summary}", _OPPORTUNITY_KEYWORDS)
        )
        significance = float(_evt_field(event, "significance_score", 0.5) or metadata.get("significance_score") or 0.5)
        confidence = float(_evt_field(event, "confidence", 0.45) or 0.45)
        if _is_url_like(raw_title):
            display_title = _title_from_docs(docs) or f"{subject} {_EVENT_LABELS.get(event_type, 'story signal')}"
        else:
            display_title = raw_title

        profiles.append(
            EventProfile(
                event_id=event_id,
                title=raw_title,
                display_title=_normalize_space(display_title),
                summary=summary or raw_title,
                event_type=event_type,
                event_family=_event_family(event_type),
                subject=subject,
                subject_key=subject_key,
                source_ids=source_ids,
                evidence_ids=evidence_ids,
                doc_ids=doc_ids,
                canonical_urls=canonical_urls,
                title_tokens=title_tokens,
                similarity_text=f"{raw_title} {summary}",
                day_bucket=event_time.date().isoformat() if event_time else None,
                event_time=event_time,
                significance_score=significance,
                confidence=confidence,
                watchlist_hits=watchlist_hits,
                topic_hits=topic_hits,
                risk_keyword_hits=risk_keyword_hits,
                opportunity_keyword_hits=opportunity_keyword_hits,
                metadata=metadata,
            )
        )
    return profiles


def _pair_merge_reasons(left: EventProfile, right: EventProfile) -> list[str]:
    reasons: list[str] = []
    evidence_overlap = set(left.evidence_ids) & set(right.evidence_ids)
    doc_overlap = set(left.doc_ids) & set(right.doc_ids)
    url_overlap = set(left.canonical_urls) & set(right.canonical_urls)
    path_overlap = {
        urlparse(url).path.rstrip("/").lower()
        for url in left.canonical_urls
        if urlparse(url).path.rstrip("/")
    } & {
        urlparse(url).path.rstrip("/").lower()
        for url in right.canonical_urls
        if urlparse(url).path.rstrip("/")
    }
    left_slug = {
        path.split("/")[-1]
        for path in (
            urlparse(url).path.rstrip("/").lower()
            for url in left.canonical_urls
        )
        if path and "/" in path
    }
    right_slug = {
        path.split("/")[-1]
        for path in (
            urlparse(url).path.rstrip("/").lower()
            for url in right.canonical_urls
        )
        if path and "/" in path
    }
    slug_overlap = left_slug & right_slug
    same_subject = bool(left.subject_key and left.subject_key == right.subject_key)
    same_window = bool(left.day_bucket and right.day_bucket and left.day_bucket == right.day_bucket)
    family_close = left.event_family == right.event_family
    title_similarity = _text_similarity(left.similarity_text, right.similarity_text)
    common_tokens = left.title_tokens & right.title_tokens

    if evidence_overlap:
        reasons.append("supporting_evidence_ids overlap")
    if doc_overlap or url_overlap:
        reasons.append("canonical document/url overlap")
    if path_overlap:
        reasons.append("canonical url path overlap")
    if slug_overlap:
        reasons.append("canonical url slug overlap")
    if same_subject and same_window:
        reasons.append("same subject + same time window")
    if family_close and title_similarity >= 0.5:
        reasons.append("title/summary similarity")

    strong_story_match = (
        same_subject
        and family_close
        and title_similarity >= 0.32
        and (same_window or len(common_tokens) >= 2)
    )
    broad_story_match = same_window and family_close and title_similarity >= 0.65
    same_story_tokens = same_subject and same_window and family_close and len(common_tokens) >= 3
    if evidence_overlap or doc_overlap or url_overlap or path_overlap or slug_overlap or strong_story_match or broad_story_match or same_story_tokens:
        return _unique(reasons) or ["title/summary similarity"]
    return []


def _cluster_events(profiles: list[EventProfile]) -> tuple[list[list[EventProfile]], dict[tuple[str, str], list[str]]]:
    parent = {profile.event_id: profile.event_id for profile in profiles}
    rank = {profile.event_id: 0 for profile in profiles}
    reasons_by_edge: dict[tuple[str, str], list[str]] = {}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            parent[left_root] = right_root
        elif rank[left_root] > rank[right_root]:
            parent[right_root] = left_root
        else:
            parent[right_root] = left_root
            rank[left_root] += 1

    for idx, left in enumerate(profiles):
        for right in profiles[idx + 1:]:
            reasons = _pair_merge_reasons(left, right)
            if not reasons:
                continue
            union(left.event_id, right.event_id)
            reasons_by_edge[tuple(sorted((left.event_id, right.event_id)))] = reasons

    grouped: dict[str, list[EventProfile]] = defaultdict(list)
    for profile in profiles:
        grouped[find(profile.event_id)].append(profile)
    clusters = []
    for cluster in grouped.values():
        clusters.append(
            sorted(
                cluster,
                key=lambda item: (-item.significance_score, -item.confidence, item.event_id),
            )
        )
    clusters.sort(key=lambda group: (-max(item.significance_score for item in group), group[0].event_id))
    return clusters, reasons_by_edge


def _trend_type_for_cluster(
    *,
    event_family: str,
    event_count: int,
    corroboration: float,
    watchlist_hits: list[str],
    topic_hits: list[str],
    risk_hits: list[str],
    opportunity_hits: list[str],
    title_text: str,
) -> str:
    lowered = title_text.lower()
    competition_hits = (
        len(watchlist_hits) >= 2
        or any(keyword in lowered for keyword in _COMPETITION_KEYWORDS)
        or event_family == "competition"
    )
    adoption_hits = (
        event_family == "adoption"
        or any(hit.endswith(":model_release") for hit in topic_hits)
        or any(keyword in lowered for keyword in _ADOPTION_KEYWORDS)
    )
    if risk_hits or event_family == "risk" or any(":risk" in hit for hit in topic_hits):
        return "risk_cluster"
    if adoption_hits:
        return "adoption_cluster"
    if opportunity_hits or event_family == "opportunity" or any(":opportunity" in hit for hit in topic_hits):
        return "opportunity_cluster"
    if competition_hits:
        return "competition_cluster"
    if event_count > 1 and corroboration >= 0.52:
        return "momentum_cluster"
    return "narrative_cluster"


def _direction_for_cluster(event_count: int, novelty: float, corroboration: float) -> str:
    if event_count >= 3 or (event_count >= 2 and novelty >= 0.58 and corroboration >= 0.5):
        return "accelerating"
    if novelty >= 0.55:
        return "emerging"
    return "stable"


def _build_cluster_title(
    representative: EventProfile,
    subject: str,
    trend_type: str,
    event_count: int,
) -> str:
    if representative.display_title and not _is_url_like(representative.display_title):
        return representative.display_title
    if event_count > 1:
        return f"{subject} {_TREND_LABELS.get(trend_type, 'story cluster')}"
    return f"{subject} {_EVENT_LABELS.get(representative.event_type, 'story signal')}"


def _route_finding(
    *,
    trend: TrendSignal,
    event_profiles: list[EventProfile],
) -> tuple[str, list[str], dict[str, float]]:
    metadata = trend.metadata or {}
    watchlist_hits = list(metadata.get("watchlist_hits") or [])
    topic_hits = list(metadata.get("topic_hits") or [])
    risk_hits = list(metadata.get("risk_keyword_hits") or [])
    opportunity_hits = list(metadata.get("opportunity_keyword_hits") or [])
    title_text = f"{trend.display_title or trend.title or ''} {trend.summary or ''}".lower()
    event_family = str(metadata.get("event_family") or "story")
    event_count = len(trend.event_ids or trend.supporting_event_ids)
    significance = float(metadata.get("significance_avg", 0.5) or 0.5)
    novelty = float(trend.novelty_score or 0.0)
    corroboration = float(trend.corroboration_score or 0.0)

    competition_hits = (
        len(watchlist_hits) >= 2
        or any(keyword in title_text for keyword in _COMPETITION_KEYWORDS)
        or event_family == "competition"
    )
    adoption_hits = (
        event_family == "adoption"
        or any(hit.endswith(":model_release") for hit in topic_hits)
        or any(keyword in title_text for keyword in _ADOPTION_KEYWORDS)
    )
    narrative_hits = event_family == "narrative" or trend.trend_type == "narrative_cluster"

    scores = {
        "risk_signal": 0.08,
        "opportunity_signal": 0.08,
        "competition_signal": 0.05,
        "adoption_signal": 0.08,
        "narrative_shift": 0.18,
        "momentum_signal": 0.15,
    }
    explain: list[str] = []

    if risk_hits or any(":risk" in hit for hit in topic_hits):
        scores["risk_signal"] += 0.52
        explain.append(f"risk cues: {', '.join((risk_hits or topic_hits)[:3])}")
    if adoption_hits:
        scores["adoption_signal"] += 0.58
        explain.append("adoption/release style event cues present")
    if opportunity_hits or any(":opportunity" in hit for hit in topic_hits):
        scores["opportunity_signal"] += 0.52
        explain.append(f"opportunity cues: {', '.join((opportunity_hits or topic_hits)[:3])}")
    if competition_hits:
        scores["competition_signal"] += 0.42
        explain.append("multiple peer/comparison cues present")
    if narrative_hits:
        scores["narrative_shift"] += 0.32
        explain.append("cluster looks like a narrative/coverage shift")
    if event_count > 1:
        scores["momentum_signal"] += 0.18
        explain.append(f"{event_count} related events merged into one story")
    if corroboration >= 0.5:
        scores["momentum_signal"] += 0.18
        scores["narrative_shift"] += 0.06
        explain.append(f"corroboration {corroboration:.2f} indicates repeated confirmation")
    if novelty >= 0.58:
        scores["momentum_signal"] += 0.12
        if not adoption_hits:
            scores["opportunity_signal"] += 0.08
        scores["narrative_shift"] += 0.05
        explain.append(f"novelty {novelty:.2f} suggests a fresh development")
    if significance >= 0.65:
        scores["risk_signal"] += 0.1
        scores["opportunity_signal"] += 0.1
        scores["momentum_signal"] += 0.12
        explain.append(f"mean significance {significance:.2f} lifts urgency")
    if watchlist_hits and not competition_hits:
        scores["adoption_signal"] += 0.05
        scores["risk_signal"] += 0.03
        scores["opportunity_signal"] += 0.03
        explain.append(f"watchlist hits: {', '.join(watchlist_hits[:3])}")
    if trend.trend_type == "risk_cluster":
        scores["risk_signal"] += 0.18
    if trend.trend_type == "opportunity_cluster":
        scores["opportunity_signal"] += 0.18
    if trend.trend_type == "adoption_cluster":
        scores["adoption_signal"] += 0.18
    if trend.trend_type == "competition_cluster":
        scores["competition_signal"] += 0.16
    if trend.trend_type == "momentum_cluster":
        scores["momentum_signal"] += 0.16
    if trend.trend_type == "narrative_cluster":
        scores["narrative_shift"] += 0.12

    # Avoid flattening into competition unless there is a real peer/comparison cue.
    if not competition_hits:
        scores["competition_signal"] -= 0.1
    if adoption_hits:
        scores["opportunity_signal"] -= 0.04

    winner = max(scores.items(), key=lambda item: (item[1], item[0]))[0]
    if scores[winner] < 0.4:
        winner = "momentum_signal" if event_count > 1 else "narrative_shift"
    return winner, _unique(explain), {key: round(value, 3) for key, value in scores.items()}


def _finding_summary_for_type(finding_type: str, trend_title: str, subject: str, event_count: int) -> str:
    label = _FINDING_LABELS.get(finding_type, "Finding")
    if finding_type == "risk_signal":
        return f"{label} for {subject}: {trend_title} ({event_count} related event(s))."
    if finding_type == "opportunity_signal":
        return f"{label} around {subject}: {trend_title}."
    if finding_type == "competition_signal":
        return f"{label} around {subject}: monitor how peers respond to {trend_title.lower()}."
    if finding_type == "adoption_signal":
        return f"{label} for {subject}: rollout or customer uptake is becoming visible."
    if finding_type == "momentum_signal":
        return f"{label}: repeated related events suggest this story is gaining traction."
    return f"{label}: this story is shaping the surrounding narrative for {subject}."


def _build_trends_and_findings(state: TideWatchState) -> tuple[list[TrendSignal], list[Finding]]:
    profiles = _build_event_profiles(state)
    if not profiles:
        return [], []

    clusters, reasons_by_edge = _cluster_events(profiles)
    trends: list[TrendSignal] = []
    findings: list[Finding] = []

    for cluster in clusters:
        representative = cluster[0]
        event_ids = [item.event_id for item in cluster]
        evidence_ids = _unique([evidence_id for item in cluster for evidence_id in item.evidence_ids])
        doc_ids = _unique([doc_id for item in cluster for doc_id in item.doc_ids])
        canonical_urls = _unique([url for item in cluster for url in item.canonical_urls])
        source_ids = _unique([source_id for item in cluster for source_id in item.source_ids])
        watchlist_hits = _unique([hit for item in cluster for hit in item.watchlist_hits])
        topic_hits = _unique([hit for item in cluster for hit in item.topic_hits])
        risk_hits = _unique([hit for item in cluster for hit in item.risk_keyword_hits])
        opportunity_hits = _unique([hit for item in cluster for hit in item.opportunity_keyword_hits])
        event_family = Counter(item.event_family for item in cluster).most_common(1)[0][0]
        event_types = _unique([item.event_type for item in cluster])
        subject_counter = Counter(item.subject for item in cluster if item.subject)
        subject = subject_counter.most_common(1)[0][0] if subject_counter else representative.subject
        significance_avg = sum(item.significance_score for item in cluster) / max(len(cluster), 1)
        confidence_avg = sum(item.confidence for item in cluster) / max(len(cluster), 1)
        source_count = max(len(source_ids), 1)
        doc_count = max(len(doc_ids), 1)
        event_count = len(cluster)
        strength = _clamp(0.3 + 0.1 * min(source_count, 3) + 0.05 * (event_count - 1) + 0.15 * max(significance_avg - 0.5, 0.0))
        corroboration = _clamp(0.4 + 0.05 * min(source_count, 3) + 0.08 * (doc_count - 1) + 0.06 * (event_count - 1))
        novelty = _clamp(
            0.32
            + 0.16 * bool(opportunity_hits or risk_hits or any(item.event_family in {"adoption", "competition"} for item in cluster))
            + 0.12 * bool(canonical_urls)
            + 0.1 * max(significance_avg - 0.45, 0.0)
            + 0.08 * bool(event_count == 1)
        )
        confidence = _clamp(confidence_avg + 0.05 * min(doc_count - 1, 2) + 0.05 * min(event_count - 1, 2), 0.35, 0.95)

        merge_reasons = []
        for idx, left in enumerate(cluster):
            for right in cluster[idx + 1:]:
                merge_reasons.extend(reasons_by_edge.get(tuple(sorted((left.event_id, right.event_id))), []))
        merge_reasons = _unique(merge_reasons)

        trend_type = _trend_type_for_cluster(
            event_family=event_family,
            event_count=event_count,
            corroboration=corroboration,
            watchlist_hits=watchlist_hits,
            topic_hits=topic_hits,
            risk_hits=risk_hits,
            opportunity_hits=opportunity_hits,
            title_text=" ".join(item.similarity_text for item in cluster[:2]),
        )
        direction = _direction_for_cluster(event_count, novelty, corroboration)
        cluster_title = _build_cluster_title(representative, subject, trend_type, event_count)
        theme = f"{subject} {_TREND_LABELS.get(trend_type, 'story cluster')}"
        trend_id = _hash_id("tr", event_ids)
        bundle_id = _hash_id("bun", event_ids)
        explain = []
        if event_count > 1:
            explain.append(f"Merged {event_count} related events into one trend.")
        if merge_reasons:
            explain.append(f"Grouping signals: {', '.join(merge_reasons)}.")
        if doc_count > 1:
            explain.append(f"Story is supported by {doc_count} canonical document(s).")
        if source_count > 1:
            explain.append(f"Coverage spans {source_count} distinct source(s).")
        if watchlist_hits:
            explain.append(f"Watchlist entity hits: {', '.join(watchlist_hits[:3])}.")
        if topic_hits:
            explain.append(f"Topic hits: {', '.join(topic_hits[:3])}.")
        if risk_hits:
            explain.append(f"Risk cues: {', '.join(risk_hits[:3])}.")
        if opportunity_hits:
            explain.append(f"Opportunity cues: {', '.join(opportunity_hits[:3])}.")
        if not explain:
            explain.append("Single event retained as its own trend because no strong merge signals were present.")
        why_it_matters = (
            f"{subject} has {event_count} related event(s) grouped into a single story. "
            f"Corroboration is {corroboration:.2f} across {doc_count} document(s) and {len(evidence_ids)} evidence item(s); "
            f"novelty is {novelty:.2f} and the story direction is {direction}."
        )
        if watchlist_hits or topic_hits:
            why_it_matters += " Watchlist context is present."

        trend = TrendSignal(
            trend_id=trend_id,
            title=cluster_title,
            display_title=cluster_title,
            summary=f"{cluster_title} ({event_count} event(s), {len(evidence_ids)} evidence item(s)).",
            subject=subject,
            theme=theme,
            trend_type=trend_type,
            direction=direction,
            strength_score=round(strength, 3),
            novelty_score=round(novelty, 3),
            corroboration_score=round(corroboration, 3),
            confidence=round(confidence, 3),
            supporting_event_ids=event_ids,
            supporting_evidence_ids=evidence_ids,
            supporting_document_ids=doc_ids,
            canonical_urls=canonical_urls,
            event_ids=event_ids,
            window={
                "start": min((item.event_time for item in cluster if item.event_time), default=None),
                "end": max((item.event_time for item in cluster if item.event_time), default=None),
                "span_days": max(1, len(_unique([item.day_bucket for item in cluster if item.day_bucket]))),
            },
            bundle_ids=[bundle_id],
            why_it_matters=why_it_matters,
            metadata={
                "merge_reasons": merge_reasons,
                "explain": explain,
                "event_types": event_types,
                "event_family": event_family,
                "watchlist_hits": watchlist_hits,
                "topic_hits": topic_hits,
                "risk_keyword_hits": risk_hits,
                "opportunity_keyword_hits": opportunity_hits,
                "source_ids": source_ids,
                "representative_event_id": representative.event_id,
                "event_count": event_count,
                "evidence_count": len(evidence_ids),
                "document_count": len(doc_ids),
                "significance_avg": round(significance_avg, 3),
            },
        )
        trends.append(trend)

        finding_type, routing_explain, routing_scores = _route_finding(trend=trend, event_profiles=cluster)
        importance = _clamp(
            0.28
            + 0.3 * significance_avg
            + 0.18 * trend.corroboration_score
            + 0.12 * max(routing_scores.values())
            + 0.06 * min(event_count - 1, 2)
            + 0.04 * bool(watchlist_hits or topic_hits)
        )
        decision_relevance = _clamp(
            0.4 * importance
            + 0.22 * max(
                routing_scores["risk_signal"],
                routing_scores["opportunity_signal"],
                routing_scores["adoption_signal"],
                routing_scores["competition_signal"],
            )
            + 0.12 * significance_avg
            + 0.08 * bool(watchlist_hits)
            + 0.06 * bool(topic_hits)
        )
        finding_title = f"{_FINDING_LABELS.get(finding_type, 'Finding')} — {trend.display_title or trend.title or trend.trend_id}"
        finding = Finding(
            finding_id=_hash_id("fd", [trend.trend_id, finding_type]),
            trend_id=trend.trend_id,
            finding_type=finding_type,
            title=finding_title,
            display_title=finding_title,
            summary=_finding_summary_for_type(finding_type, trend.display_title or trend.title or trend.theme or trend.trend_id, subject, event_count),
            subject=trend.subject,
            theme=trend.theme,
            confidence=trend.confidence,
            importance_score=round(importance, 3),
            decision_relevance_score=round(decision_relevance, 3),
            supporting_event_ids=trend.supporting_event_ids,
            supporting_evidence_ids=trend.supporting_evidence_ids,
            recommended_actions=_FINDING_ACTIONS[finding_type],
            why_it_matters=trend.why_it_matters,
            metadata={
                "trend_id": trend.trend_id,
                "bundle_ids": trend.bundle_ids,
                "trend_type": trend.trend_type,
                "watchlist_hits": watchlist_hits,
                "topic_hits": topic_hits,
                "risk_keyword_hits": risk_hits,
                "opportunity_keyword_hits": opportunity_hits,
                "explain": routing_explain,
                "routing_scores": routing_scores,
                "merge_reasons": merge_reasons,
                "event_types": event_types,
                "representative_event_id": representative.event_id,
            },
        )
        findings.append(finding)

    return trends, findings


def run_intelligence(state: TideWatchState) -> dict[str, object]:
    trends, findings = _build_trends_and_findings(state)
    alerts: list[AlertItem] = []
    briefs: list[BriefingItem] = []

    sorted_findings = sorted(findings, key=lambda item: (-item.importance_score, -item.decision_relevance_score, item.finding_id))
    for rank, finding in enumerate(sorted_findings):
        if finding.importance_score >= 0.58 or finding.decision_relevance_score >= 0.52 or rank == 0:
            level = "high" if finding.importance_score >= 0.82 else "medium"
            alerts.append(AlertItem(alert_id=f"al_{rank+1}", finding_id=finding.finding_id, level=level))
        if rank < 3:
            briefs.append(
                BriefingItem(
                    briefing_id=f"br_{rank+1}",
                    finding_id=finding.finding_id,
                    title=finding.display_title or finding.title or f"Watch item #{rank+1}",
                )
            )

    return {
        "trends": trends,
        "findings": findings,
        "alerts": alerts,
        "briefing_items": briefs,
        "intelligence_metadata": {
            "trends": len(trends),
            "findings": len(findings),
            "alerts": len(alerts),
            "briefing_items": len(briefs),
            "input_events": len(state.get("events") or []),
            "merged_events": max(0, len(state.get("events") or []) - len(trends)),
        },
    }
