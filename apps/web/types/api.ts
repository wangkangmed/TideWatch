export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface OverviewCounts {
  documents: number;
  evidence: number;
  events: number;
  trends: number;
  findings: number;
  recommendations: number;
  briefs: number;
  alerts: number;
}

export interface RunSummary {
  run_id: string;
  status: string | null;
  topic_query: string | null;
  started_at: string | null;
  finished_at: string | null;
  document_count: number;
  event_count: number;
  trend_count: number;
  finding_count: number;
  recommendation_count: number;
  brief_count: number;
}

export interface TrendSummary {
  trend_id: string;
  subject: string | null;
  theme: string | null;
  title: string | null;
  display_title: string | null;
  summary: string | null;
  trend_type: string | null;
  direction: string | null;
  strength_score: number;
  novelty_score: number;
  corroboration_score: number;
  confidence: number;
  why_it_matters: string | null;
  event_count: number;
  evidence_count: number;
  document_count: number;
  explain: string[];
  merge_reasons: string[];
  run_id: string | null;
  created_at: string | null;
}

export interface TrendDetail extends TrendSummary {
  window: Record<string, any> | null;
  event_ids: string[];
  bundle_ids: string[];
  supporting_evidence_ids: string[];
  supporting_document_ids: string[];
  canonical_urls: string[];
  related_events: Record<string, any>[];
  metadata: Record<string, any>;
}

export interface FindingSummary {
  finding_id: string;
  subject: string | null;
  theme: string | null;
  finding_type: string | null;
  title: string | null;
  display_title: string | null;
  summary: string | null;
  confidence: number;
  importance_score: number;
  decision_relevance_score: number;
  why_it_matters: string | null;
  recommended_actions: string[];
  watchlist_hits: string[];
  topic_hits: string[];
  explain: string[];
  event_count: number;
  evidence_count: number;
  run_id: string | null;
  created_at: string | null;
}

export interface FindingDetail extends FindingSummary {
  trend_id: string | null;
  supporting_event_ids: string[];
  supporting_evidence_ids: string[];
  metadata: Record<string, any>;
  related_trend: Record<string, any> | null;
  related_events: Record<string, any>[];
  related_evidence: Record<string, any>[];
  related_recommendations: Record<string, any>[];
}

export interface RecommendationSummary {
  recommendation_id: string;
  signal_id: string | null;
  recommended_action: string | null;
  priority: number;
  rationale: string | null;
  why_now: string | null;
  requires_human_review: boolean;
  finding_count: number;
  event_count: number;
  evidence_count: number;
  run_id: string | null;
  created_at: string | null;
}

export interface RecommendationDetail extends RecommendationSummary {
  supporting_finding_ids: string[];
  supporting_event_ids: string[];
  supporting_evidence_ids: string[];
  metadata: Record<string, any>;
  related_signal: Record<string, any> | null;
  related_findings: Record<string, any>[];
}

export interface BriefSummary {
  brief_id: string;
  brief_type: string | null;
  title: string | null;
  summary: string | null;
  signal_count: number;
  recommendation_count: number;
  run_id: string | null;
  created_at: string | null;
}

export interface BriefDetail extends BriefSummary {
  key_signals: string[];
  recommendations: string[];
  top_risks: string[];
  top_opportunities: string[];
  top_watch_items: string[];
  supporting_finding_ids: string[];
  supporting_event_ids: string[];
  supporting_evidence_ids: string[];
  metadata: Record<string, any>;
}

export interface EventSummary {
  event_id: string;
  event_type: string | null;
  subject: string | null;
  canonical_title: string | null;
  significance_score: number;
  confidence: number;
  evidence_count: number;
  run_id: string | null;
  created_at: string | null;
}

export interface EventDetail extends EventSummary {
  object: string | null;
  event_time: string | null;
  time_precision: string | null;
  status: string | null;
  supporting_evidence_ids: string[];
  entities: Record<string, any>;
  metadata: Record<string, any>;
  evidence_items: Record<string, any>[];
}

export interface EvidenceDetail {
  evidence_id: string;
  document_id: string | null;
  source_id: string | null;
  origin_type: string | null;
  title: string | null;
  canonical_url: string | null;
  body_text: string | null;
  source_trace: Record<string, any>;
  document: Record<string, any> | null;
  linked_events: Record<string, any>[];
  run_id: string | null;
  created_at: string | null;
}

export interface AlertSummary {
  alert_id: string;
  level: string | null;
  finding_id: string | null;
  signal_type: string | null;
  title: string | null;
  summary: string | null;
  importance_score: number;
  run_id: string | null;
  created_at: string | null;
}

export interface WatchlistSummary {
  watchlist_id: string;
  entity_count: number;
  topic_count: number;
  run_id: string | null;
  created_at: string | null;
}

export interface WatchlistEntity {
  canonical_name: string;
  entity_type: string | null;
  weight: number;
  aliases: string[];
}

export interface WatchlistTopic {
  topic_name: string;
  weight: number;
  keywords: string[];
}

export interface WatchlistDetail extends WatchlistSummary {
  entities: WatchlistEntity[];
  topics: WatchlistTopic[];
  metadata: Record<string, any>;
}

export interface OverviewResponse {
  counts: OverviewCounts;
  latest_run: RunSummary | null;
  top_trends: TrendSummary[];
  top_findings: FindingSummary[];
  top_recommendations: RecommendationSummary[];
  recent_alerts: AlertSummary[];
  latest_briefs: BriefSummary[];
}
