export function renderEvidenceCards(vEvidence = [], dEvidence = []) {
  const container = document.getElementById('evidenceContainer');
  if (!container) return;

  if (vEvidence.length === 0 && dEvidence.length === 0) {
    container.innerHTML = `<div style="color: #64748b; font-size: 11px; text-align: center; padding: 12px;">No evidence citations attached.</div>`;
    return;
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;

  // Visual Evidence Cards
  vEvidence.forEach(v => {
    html += `
      <div style="background: #1e293b; border-left: 3px solid #38bdf8; border-radius: 4px; padding: 6px 10px; font-size: 11px;">
        <div style="display: flex; justify-content: space-between; font-weight: 700; color: #38bdf8;">
          <span>[${v.id}] ${v.type} (${v.camera})</span>
          <span>${v.confidence}%</span>
        </div>
        <div style="color: #cbd5e1; margin-top: 2px;">${v.text}</div>
      </div>
    `;
  });

  // Document Evidence Cards
  dEvidence.forEach(d => {
    html += `
      <div style="background: #1e293b; border-left: 3px solid #f59e0b; border-radius: 4px; padding: 6px 10px; font-size: 11px;">
        <div style="display: flex; justify-content: space-between; font-weight: 700; color: #fbbf24;">
          <span>[${d.id}] ${d.title} (p.${d.page})</span>
          <span>Score: ${Math.round(d.score * 100)}%</span>
        </div>
        <div style="color: #cbd5e1; margin-top: 2px;">${d.snippet}</div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}
