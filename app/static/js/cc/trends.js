import { store } from './store.js';
import { getTrends } from './api.js';

let trendChartInstance = null;

export async function renderTrends() {
  const canvas = document.getElementById('trendChart');
  if (!canvas || !window.Chart) return;

  try {
    const data = await getTrends(store.filters);
    if (!data) return;

    if (trendChartInstance) {
      trendChartInstance.destroy();
    }

    trendChartInstance = new window.Chart(canvas, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Compliance %',
            data: data.compliance,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.3,
            fill: true,
            yAxisID: 'y'
          },
          {
            label: 'Violations',
            data: data.violations,
            borderColor: '#f59e0b',
            borderDash: [4, 4],
            tension: 0.2,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94a3b8', font: { size: 10 } } }
        },
        scales: {
          x: { ticks: { color: '#64748b', font: { size: 9 } }, grid: { display: false } },
          y: { min: 70, max: 100, ticks: { color: '#64748b', font: { size: 9 } }, grid: { color: '#1e293b' } },
          y1: { position: 'right', ticks: { color: '#64748b', font: { size: 9 } }, grid: { display: false } }
        }
      }
    });
  } catch (err) {
    console.error('Failed to render Trend chart:', err);
  }
}
