/**
 * Central API client for Mission Control with AbortController debounce support.
 */
let currentAbortController = null;

export async function fetchWithAbort(url, options = {}) {
  if (currentAbortController) {
    currentAbortController.abort();
  }
  currentAbortController = new AbortController();
  const { signal } = currentAbortController;

  try {
    const res = await fetch(url, { ...options, signal });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    if (err.name === 'AbortError') return null;
    throw err;
  }
}

export async function getKpis(filters = {}) {
  const p = new URLSearchParams(filters).toString();
  const res = await fetch(`/api/command-center/kpis?${p}`);
  return await res.json();
}

export async function getHeatmap(filters = {}) {
  const p = new URLSearchParams(filters).toString();
  const res = await fetch(`/api/command-center/heatmap?${p}`);
  return await res.json();
}

export async function getTrends(filters = {}) {
  const p = new URLSearchParams(filters).toString();
  const res = await fetch(`/api/command-center/trends?${p}`);
  return await res.json();
}

export async function getFeed(limit = 15) {
  const res = await fetch(`/api/command-center/feed?limit=${limit}`);
  return await res.json();
}

export async function getZones() {
  const res = await fetch(`/api/command-center/zones`);
  return await res.json();
}

export async function askCopilot(question, uiContext = {}) {
  const res = await fetch("/api/copilot/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, ui_context: uiContext })
  });
  return await res.json();
}

export async function getSuggestions() {
  const res = await fetch("/api/copilot/suggestions");
  return await res.json();
}

export async function getGraphMeta() {
  const res = await fetch("/api/copilot/graph");
  return await res.json();
}

export async function getRunEvents(runId) {
  const res = await fetch(`/api/copilot/runs/${runId}/events`);
  return await res.json();
}
