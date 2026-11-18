import { store } from './store.js';
import { renderKpis } from './kpi.js';
import { initSiteMap } from './sitemap.js';
import { renderHeatmap } from './heatmap.js';
import { renderTrends } from './trends.js';
import { renderLiveFeed } from './feed.js';
import { initCopilot } from './copilot.js';
import { initPipelineViz } from './pipeline_viz.js';
import { initVoice } from './voice.js';
import { initBriefing } from './briefing.js';
import { initDemoMode } from './demo_mode.js';
import { initScoreboard } from './scoreboard.js';
import { replayRun } from './replay.js';

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Initial renders
  renderChipBar();
  await initPipelineViz();
  await renderKpis();
  await initSiteMap();
  await renderHeatmap();
  await renderTrends();
  await renderLiveFeed();
  await initCopilot();

  // 2. Initialise new M4 modules
  initVoice({
    inputEl: document.getElementById('copilotInput'),
    micBtn: document.getElementById('micBtn'),
    submitFn: (text) => window.sendCopilotQuery?.(text),
  });

  initBriefing({
    store: { getState: () => ({ kpis: store.filters }) },
    sendQueryFn: (q) => window.sendCopilotQuery?.(q),
  });

  initDemoMode({
    sendQueryFn: (q) => window.sendCopilotQuery?.(q),
  });

  initScoreboard({
    replayFn: (runId) => replayRun(runId),
  });

  // 3. Ctrl+K shortcut → focus Copilot input
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const input = document.getElementById('copilotInput');
      if (input) {
        input.focus();
        input.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  });

  // 4. Fullscreen toggle
  const fsBtn = document.getElementById('fullscreenBtn');
  if (fsBtn && document.fullscreenEnabled) {
    fsBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
    document.addEventListener('fullscreenchange', () => {
      fsBtn.textContent = document.fullscreenElement ? '⊡ Exit' : '⛶ Fullscreen';
    });
  } else if (fsBtn) {
    fsBtn.style.display = 'none'; // hide if not supported
  }

  // 5. Subscribe to store changes (Debounced reactive updates)
  let debounceTimer = null;
  store.subscribe((filters) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      renderChipBar();
      await renderKpis();
      await initSiteMap();
      await renderHeatmap();
      await renderTrends();
    }, 150);
  });

  // 6. Periodic real-time live feed refresh (every 8s)
  setInterval(() => {
    renderLiveFeed();
  }, 8000);
});

function renderChipBar() {
  const container = document.getElementById('activeFiltersBar');
  if (!container) return;

  const f = store.filters;
  const active = [];

  if (f.zone) active.push({ key: 'zone', label: `Zone: ${f.zone}` });
  if (f.violationType) active.push({ key: 'violationType', label: `Type: ${f.violationType}` });
  if (f.severity) active.push({ key: 'severity', label: `Severity: ${f.severity}` });

  if (active.length === 0) {
    container.innerHTML = `<span style="color: #9A6B7E; font-size: 11px;">No active filters. Click zones or metrics to filter.</span>`;
    return;
  }

  container.innerHTML = active.map(a => `
    <span class="cc-chip">
      ${a.label}
      <span class="cc-chip-close" onclick="window.removeFilter('${a.key}')">✕</span>
    </span>
  `).join('') + `
    <button class="btn btn-secondary btn-sm" style="font-size: 10px; padding: 2px 8px;" onclick="window.clearAllFilters()">
      Clear All
    </button>
  `;

  window.removeFilter = (key) => store.setFilter(key, null);
  window.clearAllFilters = () => store.clearFilters();
}
