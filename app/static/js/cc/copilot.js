import { store } from './store.js';
import { askCopilot, getSuggestions } from './api.js';
import { initPipelineViz, setNodeActive, setNodeCompleted, resetPipelineViz } from './pipeline_viz.js';
import { renderTrustMeter } from './trust_meter.js';
import { renderEvidenceCards } from './evidence.js';
import { refreshScoreboard } from './scoreboard.js';

let activeEventSource = null;

export async function initCopilot() {
  const input = document.getElementById('copilotInput');
  const sendBtn = document.getElementById('copilotSendBtn');
  const suggestionsBox = document.getElementById('copilotSuggestions');

  // Load suggestions
  try {
    const data = await getSuggestions();
    if (data.suggestions && suggestionsBox) {
      suggestionsBox.innerHTML = data.suggestions.slice(0, 3).map(s => `
        <button class="btn btn-secondary btn-sm" style="font-size: 10px; padding: 2px 8px; border-radius: 12px; white-space: nowrap;" onclick="window.sendCopilotQuery('${s.replace(/'/g, "\\'")}')">
          💡 ${s}
        </button>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load suggestions:', err);
  }

  window.sendCopilotQuery = (query) => {
    if (input) {
      input.value = query;
      handleSend();
    }
  };

  sendBtn?.addEventListener('click', handleSend);
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSend();
  });

  async function handleSend() {
    const q = input.value.trim();
    if (!q) return;

    input.value = '';
    resetPipelineViz();
    showAnswerLoading(q);

    try {
      const res = await askCopilot(q, store.filters);
      if (res.run_id) {
        connectStream(res.run_id);
      }
    } catch (err) {
      showAnswerError('Failed to dispatch query: ' + err.message);
    }
  }
}

function connectStream(runId) {
  if (activeEventSource) {
    activeEventSource.close();
  }

  activeEventSource = new EventSource(`/api/copilot/stream/${runId}`);

  activeEventSource.addEventListener('node_started', (e) => {
    const data = JSON.parse(e.data);
    setNodeActive(data.node_name);
  });

  activeEventSource.addEventListener('node_finished', (e) => {
    const data = JSON.parse(e.data);
    setNodeCompleted(data.node_name);
  });

  activeEventSource.addEventListener('final', (e) => {
    const data = JSON.parse(e.data);
    renderFinalResponse(data);
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
  });

  activeEventSource.addEventListener('error', (e) => {
    console.warn('SSE stream error, falling back to polling:', e);
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
    pollRunResult(runId);
  });
}

async function pollRunResult(runId) {
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const res = await fetch(`/api/copilot/runs/${runId}`);
      const data = await res.json();
      if (data.status === 'completed' && data.run) {
        renderFinalResponse(data.run);
        break;
      }
    } catch (err) {
      break;
    }
  }
}

function showAnswerLoading(question) {
  const card = document.getElementById('copilotAnswerBox');
  if (card) {
    card.innerHTML = `
      <div style="color: #38bdf8; font-size: 13px; font-weight: 700; margin-bottom: 6px;">
        Executing LangGraph Pipeline...
      </div>
      <div style="font-size: 12px; color: #94a3b8;">"${question}"</div>
    `;
  }
}

function showAnswerError(msg) {
  const card = document.getElementById('copilotAnswerBox');
  if (card) {
    card.innerHTML = `<div style="color: #f87171; font-size: 12px;">${msg}</div>`;
  }
}

function renderFinalResponse(payload) {
  const card = document.getElementById('copilotAnswerBox');
  if (!card) return;

  const aCard = payload.answer_card || {};
  const val = payload.validation || {};
  const vEv = payload.visual_evidence || [];
  const dEv = payload.document_evidence || [];

  // Format citations into clickable UI spans
  let ansText = aCard.answer || 'No response generated.';
  ansText = ansText.replace(/\[(V\d+|D\d+)\]/g, '<span class="cite-tag">[$1]</span>');

  let keyFactsHtml = '';
  if (aCard.key_facts && aCard.key_facts.length > 0) {
    keyFactsHtml = `
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
        ${aCard.key_facts.map(f => `
          <div style="background: #1e293b; padding: 4px 8px; border-radius: 4px; font-size: 11px;">
            <span style="color: #94a3b8;">${f.label}:</span> <strong style="color: #f8fafc;">${f.value}</strong>
          </div>
        `).join('')}
      </div>
    `;
  }

  let actionsHtml = '';
  if (aCard.recommended_actions && aCard.recommended_actions.length > 0) {
    actionsHtml = `
      <div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 8px;">
        <span style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Recommended Actions:</span>
        <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 12px; color: #cbd5e1;">
          ${aCard.recommended_actions.map(act => `<li>${act.action}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  // Follow-up questions as clickable chips
  let followUpHtml = '';
  const followUps = aCard.follow_up_questions || payload.follow_up_questions || [];
  if (followUps.length > 0) {
    followUpHtml = `
      <div style="margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 8px;">
        <span style="font-size: 11px; font-weight: 700; color: #a78bfa; text-transform: uppercase;">Follow-up Questions:</span>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px;">
          ${followUps.map(q => `
            <button class="btn btn-secondary btn-sm follow-up-chip"
                    style="font-size: 10px; padding: 3px 10px; border-radius: 12px; cursor: pointer; white-space: nowrap; max-width: 260px; overflow: hidden; text-overflow: ellipsis;"
                    title="${q.replace(/"/g, '&quot;')}"
                    onclick="window.sendCopilotQuery('${q.replace(/'/g, "\\'")}')"
            >💡 ${q}</button>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Clipboard copy button
  const copyBtnId = 'copy-answer-btn-' + Date.now();

  card.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
      <h3 class="answer-headline">${aCard.headline || 'SafeSight AI Analysis'}</h3>
      <div style="display: flex; gap: 6px; align-items: center;">
        <button id="${copyBtnId}" class="btn btn-secondary btn-sm" style="font-size: 10px; padding: 2px 8px;" title="Copy answer to clipboard">📋 Copy</button>
        <span class="pill ${aCard.risk_level === 'CRITICAL' || aCard.risk_level === 'HIGH' ? 'pill-high' : 'pill-medium'}">
          ${aCard.risk_level || 'LOW'} RISK
        </span>
      </div>
    </div>
    <div class="answer-text" style="margin-top: 8px;">${ansText}</div>
    ${keyFactsHtml}
    ${actionsHtml}
    ${followUpHtml}
  `;

  // Wire clipboard button
  const copyBtn = document.getElementById(copyBtnId);
  if (copyBtn && navigator.clipboard) {
    copyBtn.addEventListener('click', async () => {
      try {
        const plainText = (aCard.answer || 'No response.').replace(/\[([VD]\d+)\]/g, '[$1]');
        await navigator.clipboard.writeText(plainText);
        copyBtn.textContent = '✅ Copied!';
        setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
      } catch (err) {
        copyBtn.textContent = '❌ Failed';
        setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
      }
    });
  } else if (copyBtn) {
    copyBtn.style.display = 'none'; // hide if Clipboard API not available
  }

  // Render Trust Meter
  renderTrustMeter(val);

  // Render Evidence tab
  renderEvidenceCards(vEv, dEv);

  // Refresh scoreboard with the new run
  try { refreshScoreboard(); } catch (_) { /* scoreboard not initialised yet */ }
}
