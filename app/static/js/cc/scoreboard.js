/**
 * scoreboard.js — Quality Scoreboard for SafeSight Mission Control.
 *
 * Renders a sortable run-history leaderboard inside `#scoreboard-panel`.
 * Columns: Rank, Query (truncated), Trust Score, Latency, Nodes Visited, Time, Replay.
 *
 * Data comes from GET /api/copilot/history (already implemented in copilot.py).
 * The Replay button delegates to the existing replayRun() in replay.js.
 *
 * Usage:
 *   import { initScoreboard, refreshScoreboard } from './scoreboard.js';
 *   initScoreboard({ replayFn });
 *   // Call refreshScoreboard() whenever you want a fresh pull.
 */

'use strict';

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

/** @type {Array<object>} */
let _runs = [];

/** @type {'trust' | 'latency' | 'time'} */
let _sortKey = 'trust';

/** @type {boolean} */
let _sortAsc = false;

/** @type {((runId: string) => void) | null} */
let _replayFn = null;

/** @type {HTMLElement | null} */
let _container = null;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Fetch the latest run history from the API.
 * @returns {Promise<Array<object>>}
 */
async function _fetchHistory() {
  try {
    const res = await fetch('/api/copilot/history', { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.runs ?? []);
  } catch (err) {
    console.warn('[scoreboard] fetch failed:', err);
    return [];
  }
}

/**
 * Sort runs by the current sort key.
 * @param {Array<object>} runs
 * @returns {Array<object>}
 */
function _sort(runs) {
  const sorted = [...runs].sort((a, b) => {
    let av, bv;
    if (_sortKey === 'trust') {
      av = a.trust_score ?? 0;
      bv = b.trust_score ?? 0;
    } else if (_sortKey === 'latency') {
      av = a.latency_ms ?? Infinity;
      bv = b.latency_ms ?? Infinity;
    } else {
      // time — sort by created_at string (ISO)
      av = a.created_at ?? '';
      bv = b.created_at ?? '';
    }
    if (av < bv) return _sortAsc ? -1 : 1;
    if (av > bv) return _sortAsc ? 1 : -1;
    return 0;
  });
  return sorted;
}

/**
 * Render the scoreboard table into _container.
 */
function _render() {
  if (!_container) return;

  const sorted = _sort(_runs);

  if (sorted.length === 0) {
    _container.innerHTML =
      '<p class="cc-empty-state" style="padding:1.5rem;text-align:center;color:var(--cc-text-muted)">No copilot runs yet. Ask a question to see your score!</p>';
    return;
  }

  /**
   * @param {string} key
   * @returns {string}  Arrow indicator for sort column header
   */
  const arrow = (key) => {
    if (key !== _sortKey) return '<span style="opacity:.3">⇅</span>';
    return _sortAsc ? '↑' : '↓';
  };

  const headerCols = [
    { key: null,      label: '#' },
    { key: null,      label: 'Query' },
    { key: 'trust',   label: `Trust ${arrow('trust')}` },
    { key: 'latency', label: `Latency ${arrow('latency')}` },
    { key: null,      label: 'Nodes' },
    { key: 'time',    label: `Time ${arrow('time')}` },
    { key: null,      label: '' },
  ];

  const ths = headerCols
    .map(({ key, label }) => {
      const sortable = key ? `style="cursor:pointer;user-select:none;" data-sort="${key}"` : '';
      return `<th ${sortable}>${label}</th>`;
    })
    .join('');

  /**
   * Trust score badge colour.
   * @param {number} score
   */
  const trustColor = (score) => {
    if (score >= 80) return '#22B573';
    if (score >= 50) return '#FF9F1C';
    return '#E53950';
  };

  const rows = sorted
    .map((run, i) => {
      const rank     = i + 1;
      const query    = _esc(run.query ?? '').slice(0, 60) + (run.query?.length > 60 ? '…' : '');
      const trust    = typeof run.trust_score === 'number' ? run.trust_score : '—';
      const latency  = run.latency_ms != null ? `${run.latency_ms} ms` : '—';
      const nodes    = run.nodes_visited ?? '—';
      const time     = run.created_at ? _fmtTime(run.created_at) : '—';
      const runId    = _esc(run.run_id ?? '');
      const color    = typeof trust === 'number' ? trustColor(trust) : '#9A6B7E';
      const trustBadge =
        typeof trust === 'number'
          ? `<span style="color:${color};font-weight:700">${trust}</span>`
          : '—';

      return `<tr>
        <td style="color:var(--cc-text-muted);text-align:center">${rank}</td>
        <td title="${_esc(run.query ?? '')}" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${query}</td>
        <td style="text-align:center">${trustBadge}</td>
        <td style="text-align:center">${latency}</td>
        <td style="text-align:center">${nodes}</td>
        <td style="text-align:center;color:var(--cc-text-secondary)">${time}</td>
        <td style="text-align:center">
          ${runId ? `<button class="cc-btn cc-btn-sm replay-btn" data-run-id="${runId}" title="Replay this run">▶ Replay</button>` : ''}
        </td>
      </tr>`;
    })
    .join('');

  _container.innerHTML = `
    <table class="scoreboard-table" style="width:100%;border-collapse:collapse;font-size:.85rem;">
      <thead>
        <tr style="border-bottom:1px solid var(--cc-border)">${ths}</tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Sort click handlers
  _container.querySelectorAll('th[data-sort]').forEach((th) => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      if (_sortKey === key) {
        _sortAsc = !_sortAsc;
      } else {
        _sortKey = key;
        _sortAsc = key === 'latency'; // latency: ascending = fastest first
      }
      _render();
    });
  });

  // Replay button handlers
  _container.querySelectorAll('.replay-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const runId = btn.dataset.runId;
      if (runId && _replayFn) {
        _replayFn(runId);
      }
    });
  });
}

/**
 * Escape HTML special characters.
 * @param {string} str
 * @returns {string}
 */
function _esc(str) {
  return str.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );
}

/**
 * Format an ISO timestamp to a short local time string.
 * @param {string} iso
 * @returns {string}
 */
function _fmtTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialise the scoreboard.
 *
 * @param {{
 *   replayFn?:    (runId: string) => void,
 *   containerId?: string,
 * }} opts
 */
export function initScoreboard({ replayFn, containerId = 'scoreboard-panel' } = {}) {
  _container = document.getElementById(containerId);
  _replayFn = replayFn ?? null;

  if (!_container) return; // widget not on this page

  refreshScoreboard();
}

/**
 * Pull fresh data from the API and re-render.
 */
export async function refreshScoreboard() {
  if (!_container) return;
  _runs = await _fetchHistory();
  _render();
}
