export function renderEvidenceCards(vEvidence = [], dEvidence = []) {
  const container = document.getElementById('evidenceContainer');
  if (!container) return;

  if (vEvidence.length === 0 && dEvidence.length === 0) {
    container.innerHTML = `<div style="color: #9A6B7E; font-size: 11px; text-align: center; padding: 12px;">No evidence citations attached.</div>`;
    return;
  }

  let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;

  // Visual Evidence Cards
  vEvidence.forEach(v => {
    html += `
      <div style="background: #FFFDF9; border: 1px solid #F3D9CF; border-left: 3.5px solid #FF6B4A; border-radius: 6px; padding: 6px 10px; font-size: 11px;">
        <div style="display: flex; justify-content: space-between; font-weight: 700; color: #FF6B4A;">
          <span>[${v.id}] ${v.type} (${v.camera})</span>
          <span>${v.confidence}%</span>
        </div>
        <div style="color: #4A1D2F; margin-top: 2px;">${v.text}</div>
      </div>
    `;
  });

  // Document Evidence Cards
  dEvidence.forEach(d => {
    html += `
      <div style="background: #FFFDF9; border: 1px solid #F3D9CF; border-left: 3.5px solid #FF9F1C; border-radius: 6px; padding: 6px 10px; font-size: 11px;">
        <div style="display: flex; justify-content: space-between; font-weight: 700; color: #FF9F1C;">
          <span>[${d.id}] ${d.title} (p.${d.page})</span>
          <span>Score: ${Math.round(d.score * 100)}%</span>
        </div>
        <div style="color: #4A1D2F; margin-top: 2px;">${d.snippet}</div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}
