export function renderTrustMeter(valReport) {
  const container = document.getElementById('trustMeterBox');
  if (!container) return;

  const score = valReport ? valReport.score : 0;
  const verdict = valReport ? valReport.verdict : 'pass';
  const checks = valReport ? (valReport.checks || []) : [];

  let html = `
    <div style="display: flex; justify-content: space-between; align-items: baseline; font-size: 11px;">
      <span style="font-weight: 700; color: #6B3A4D;">TRUST METER</span>
      <strong style="color: ${score >= 80 ? '#22B573' : (score >= 50 ? '#FF9F1C' : '#E53950')}; font-size: 13px; font-weight: 800;">
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
      <div style="display: flex; justify-content: space-between; font-size: 10px; color: ${c.passed ? '#4A1D2F' : '#E53950'}; font-weight: ${c.passed ? '500' : '700'};">
        <span>${c.passed ? '✓' : '✗'} ${c.name}</span>
        <span>${c.score}%</span>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}
