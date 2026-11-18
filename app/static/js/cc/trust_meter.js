export function renderTrustMeter(valReport) {
  const container = document.getElementById('trustMeterBox');
  if (!container) return;

  const score = valReport ? valReport.score : 0;
  const verdict = valReport ? valReport.verdict : 'pass';
  const checks = valReport ? (valReport.checks || []) : [];

  let html = `
    <div style="display: flex; justify-content: space-between; align-items: baseline; font-size: 11px;">
      <span style="font-weight: 700; color: #94a3b8;">TRUST METER</span>
      <strong style="color: ${score >= 80 ? '#34d399' : (score >= 50 ? '#fcd34d' : '#f87171')}; font-size: 13px;">
        ${score}% (${verdict.toUpperCase()})
      </strong>
    </div>
    <div class="trust-meter-gauge">
      <div class="trust-meter-fill" style="width: ${score}%;"></div>
    </div>
    <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 8px;">
  `;

  checks.forEach(c => {
    html += `
      <div style="display: flex; justify-content: space-between; font-size: 10px; color: ${c.passed ? '#cbd5e1' : '#fca5a5'};">
        <span>${c.passed ? '✓' : '✗'} ${c.name}</span>
        <span>${c.score}%</span>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}
