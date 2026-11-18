/**
 * SafeSight AI - Milestone 2: Knowledge Base Search & Q&A Frontend
 */

let activeMode = 'search';

document.addEventListener('DOMContentLoaded', () => {
  // If query string has ?q=
  const urlParams = new URLSearchParams(window.location.search);
  const q = urlParams.get('q');
  if (q) {
    document.getElementById('knowledgeSearchInput').value = q;
    executeKnowledgeSearch();
  }
});

function setKnowledgeMode(mode) {
  activeMode = mode;
  const searchSec = document.getElementById('sectionSearch');
  const askSec = document.getElementById('sectionAsk');
  const tabSearch = document.getElementById('tabBtnSearch');
  const tabAsk = document.getElementById('tabBtnAsk');
  const qaCard = document.getElementById('qaAnswerCard');

  if (mode === 'search') {
    searchSec.style.display = 'block';
    askSec.style.display = 'none';
    tabSearch.classList.add('active');
    tabAsk.classList.remove('active');
    qaCard.style.display = 'none';
  } else {
    searchSec.style.display = 'none';
    askSec.style.display = 'block';
    tabSearch.classList.remove('active');
    tabAsk.classList.add('active');
  }
}

function setQuery(text) {
  const askInput = document.getElementById('askQuestionInput');
  const searchInput = document.getElementById('knowledgeSearchInput');
  if (askInput) askInput.value = text;
  if (searchInput) searchInput.value = text;

  if (activeMode === 'ask') {
    executeAskQuestion();
  } else {
    executeKnowledgeSearch();
  }
}

/* --------------------------------------------------------------------------
   Search Execution
   -------------------------------------------------------------------------- */

function executeKnowledgeSearch() {
  const q = document.getElementById('knowledgeSearchInput')?.value.trim();
  if (!q) return;

  const mode = document.getElementById('searchModeSelect')?.value || 'hybrid';
  const repo = document.getElementById('searchRepoSelect')?.value || '';
  const ppe = document.getElementById('searchPpeSelect')?.value || '';

  const resultsList = document.getElementById('resultsList');
  const meta = document.getElementById('resultsMeta');
  resultsList.innerHTML = '<div style="padding: 32px; text-align: center; color: var(--text-muted);">Searching knowledge repositories...</div>';

  fetch(`/api/knowledge/search?q=${encodeURIComponent(q)}&mode=${mode}&repository=${repo}&ppe=${ppe}`)
    .then(r => r.json())
    .then(data => {
      meta.innerText = `${data.count} result(s) in ${data.took_ms} ms (${data.mode.toUpperCase()})`;
      renderSearchResults(data.results);
    })
    .catch(err => {
      resultsList.innerHTML = `<div style="padding: 24px; color: var(--danger);">Search failed: ${err.message}</div>`;
    });
}

function renderSearchResults(results) {
  const container = document.getElementById('resultsList');
  if (!container) return;

  if (results.length === 0) {
    container.innerHTML = `
      <div class="card" style="padding: 40px; text-align: center; color: var(--text-muted);">
        <p style="font-size: 15px; font-weight: 600; margin-bottom: 4px;">No matching documents or rules found</p>
        <p style="font-size: 13px; margin: 0;">Try broadening your search keywords or switching to Semantic mode.</p>
      </div>
    `;
    return;
  }

  let html = '';
  results.forEach(res => {
    const icon = res.doc_type === 'inspection_report' ? '📋' : '📖';
    html += `
      <div class="card" style="padding: 18px 22px; display: flex; flex-direction: column; gap: 10px; transition: transform 0.15s ease;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span>${icon}</span>
            <a href="/documents/${res.document_id}" style="font-weight: 700; font-size: 15px; color: var(--text-main); text-decoration: none;">
              ${escapeHtml(res.doc_title)}
            </a>
            <span style="font-size: 11px; background: var(--bg-surface-alt); border: 1px solid var(--border-color); padding: 2px 6px; border-radius: 4px; color: var(--text-muted);">
              Page ${res.page_no}
            </span>
          </div>
          <span style="font-size: 11px; font-weight: 700; color: var(--accent); background: rgba(249, 115, 22, 0.1); padding: 2px 8px; border-radius: 10px;">
            Score: ${res.score}
          </span>
        </div>

        <div style="font-size: 13px; color: var(--text-main); line-height: 1.6; background: var(--bg-surface-alt); padding: 12px; border-radius: var(--radius-sm); border-left: 3px solid var(--accent);">
          ${res.snippet}
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-muted);">
          <span>Repository: <strong>${escapeHtml(res.repo_name || 'General')}</strong></span>
          <div style="display: flex; gap: 8px;">
            <a href="/documents/${res.document_id}" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;">Open Document</a>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

/* --------------------------------------------------------------------------
   Ask Question (Q&A)
   -------------------------------------------------------------------------- */

function executeAskQuestion() {
  const q = document.getElementById('askQuestionInput')?.value.trim();
  if (!q) return;

  const qaCard = document.getElementById('qaAnswerCard');
  const answerText = document.getElementById('qaAnswerText');
  const citationsList = document.getElementById('qaCitationsList');
  const modeBadge = document.getElementById('qaModeBadge');

  qaCard.style.display = 'block';
  answerText.innerText = 'Analyzing knowledge base documents and synthesizing answer...';
  citationsList.innerHTML = '';

  fetch('/api/knowledge/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q })
  })
    .then(r => r.json())
    .then(data => {
      answerText.innerText = data.answer || 'I could not find this in the documents.';
      modeBadge.innerText = (data.mode_used || 'extractive').toUpperCase() + ' MODE';

      // Render citations
      let cHtml = '';
      (data.citations || []).forEach(c => {
        cHtml += `
          <a href="/documents/${c.document_id}" style="text-decoration: none; display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; background: var(--bg-surface-alt); border: 1px solid var(--border-color); color: var(--text-main);">
            <span>📑</span>
            <span>${escapeHtml(c.doc_title)} (p.${c.page_no})</span>
          </a>
        `;
      });
      citationsList.innerHTML = cHtml || '<span style="font-size: 12px; color: var(--text-muted);">No direct citations found.</span>';

      // Also render source chunks in the search section below
      renderSearchResults(data.chunks || []);
      document.getElementById('resultsHeader').innerText = 'Retrieved Knowledge Chunks';
    })
    .catch(err => {
      answerText.innerText = 'Error generating answer: ' + err.message;
    });
}

function rebuildKnowledgeIndex() {
  showToast('Rebuilding similarity index across all documents...', 'info');
  fetch('/api/knowledge/rebuild', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      showToast(`Knowledge index rebuilt successfully with ${d.chunk_count} chunks!`, 'success');
    })
    .catch(e => showToast('Rebuild failed: ' + e.message, 'error'));
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
