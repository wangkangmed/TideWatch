const API_BASE = "/api/v1";

async function fetchAPI<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, String(v));
      }
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export function getOverview(runId?: string) {
  return fetchAPI<any>(`${API_BASE}/overview`, { run_id: runId });
}

export function getTrends(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/trends`, params);
}

export function getTrend(trendId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/trends/${trendId}`, { run_id: runId });
}

export function getFindings(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/findings`, params);
}

export function getFinding(findingId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/findings/${findingId}`, { run_id: runId });
}

export function getRecommendations(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/recommendations`, params);
}

export function getRecommendation(recId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/recommendations/${recId}`, { run_id: runId });
}

export function getBriefs(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/briefs`, params);
}

export function getBrief(briefId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/briefs/${briefId}`, { run_id: runId });
}

export function getAlerts(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/alerts`, params);
}

export function getEvents(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/events`, params);
}

export function getEvent(eventId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/events/${eventId}`, { run_id: runId });
}

export function getEvidence(evidenceId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/evidence/${evidenceId}`, { run_id: runId });
}

export function getWatchlists(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/watchlists`, params);
}

export function getWatchlist(watchlistId: string, runId?: string) {
  return fetchAPI<any>(`${API_BASE}/watchlists/${watchlistId}`, { run_id: runId });
}

export function getRuns(params?: Record<string, any>) {
  return fetchAPI<any>(`${API_BASE}/runs`, params);
}

export function getRun(runId: string) {
  return fetchAPI<any>(`${API_BASE}/runs/${runId}`);
}
