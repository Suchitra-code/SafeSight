/**
 * briefing.js — "Daily Briefing" auto-query for Mission Control.
 *
 * When the user clicks the "Daily Briefing" button (id="briefing-btn") the
 * module builds a context-aware natural-language question using live KPI data
 * already in the store, submits it to the Copilot, and scrolls the panel into
 * view.
 *
 * The question changes by time-of-day so it always feels relevant:
 *   • Morning (00–11): "What happened overnight?"
 *   • Daytime (12–17): "Summarise today's safety situation so far."
 *   • Evening (18–23): "Give me an end-of-day safety briefing."
 *
 * Usage:
 *   import { initBriefing } from './briefing.js';
 *   initBriefing({ store, sendQueryFn });
 */

'use strict';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a context-aware briefing question.
 * @param {{ violations_today?: number, compliance_rate?: number, active_zones?: number }} kpis
 * @returns {string}
 */
function _buildBriefingQuestion(kpis) {
  const hour = new Date().getHours();
  const compliance =
    kpis.compliance_rate != null
      ? ` Compliance is currently at ${Math.round(kpis.compliance_rate)}%.`
      : '';
  const violations =
    kpis.violations_today != null
      ? ` There have been ${kpis.violations_today} violations logged today.`
      : '';

  if (hour < 12) {
    return `Give me a morning safety briefing.${violations}${compliance} What are the key overnight incidents I should know about, and what should the team focus on first?`;
  }
  if (hour < 18) {
    return `Summarise the current safety situation.${violations}${compliance} Which zones need attention and are there any recurring violations I should escalate?`;
  }
  return `Give me an end-of-day safety briefing.${violations}${compliance} What were the top incidents today and what actions should be taken before the next shift?`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialise the Daily Briefing button.
 *
 * @param {{
 *   store:        { getState: () => { kpis?: object } },
 *   sendQueryFn:  (question: string) => void,
 *   btnId?:       string,  // defaults to 'briefing-btn'
 * }} opts
 */
export function initBriefing({ store, sendQueryFn, btnId = 'briefing-btn' }) {
  const btn = document.getElementById(btnId);
  if (!btn) return; // button not present on this page

  btn.addEventListener('click', () => {
    const kpis = store.getState?.()?.kpis ?? {};
    const question = _buildBriefingQuestion(kpis);

    // Fill the copilot input so the user can see what was sent.
    const inputEl = document.getElementById('copilot-input');
    if (inputEl) {
      inputEl.value = question;
      inputEl.dispatchEvent(new Event('input'));
    }

    // Scroll the copilot panel into view.
    const panel = document.getElementById('copilot-panel');
    if (panel) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Submit the query.
    sendQueryFn(question);

    // Provide brief visual feedback on the button.
    btn.disabled = true;
    btn.textContent = '⏳ Generating briefing…';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = '📋 Daily Briefing';
    }, 8000);
  });
}
