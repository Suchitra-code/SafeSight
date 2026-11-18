import { store } from './store.js';
import { getKpis } from './api.js';

export async function renderKpis() {
  const container = document.getElementById('kpiStrip');
  if (!container) return;

  try {
    const data = await getKpis(store.filters);
    if (!data) return;

    const cards = [
      { id: 'workers', label: 'Workers Monitored', val: data.workers_detected.value, delta: data.workers_detected.change },
      { id: 'compliance', label: 'Overall Compliance', val: data.compliance_rate.value, delta: data.compliance_rate.change },
      { id: 'violations', label: 'Active Violations', val: data.violations_today.value, delta: data.violations_today.change },
      { id: 'findings', label: 'Open Findings', val: data.open_findings.value, delta: data.open_findings.change },
      { id: 'trust', label: 'Copilot Trust Avg', val: data.avg_trust.value, delta: data.avg_trust.change }
    ];

    container.innerHTML = cards.map(c => `
      <div class="cc-kpi-card" data-kpi="${c.id}">
        <div class="cc-kpi-label">${c.label}</div>
        <div class="cc-kpi-val-row">
          <span class="cc-kpi-val">${c.val}</span>
          <span class="cc-kpi-delta">${c.delta}</span>
        </div>
      </div>
    `).join('');

    // Attach click filters
    container.querySelectorAll('.cc-kpi-card').forEach(card => {
      card.addEventListener('click', () => {
        const kpi = card.dataset.kpi;
        if (kpi === 'violations') store.setFilter('severity', 'HIGH');
      });
    });
  } catch (err) {
    console.error('Failed to render KPIs:', err);
  }
}
