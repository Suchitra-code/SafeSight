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
            borderColor: '#22B573',
            backgroundColor: 'rgba(34, 181, 115, 0.15)',
            tension: 0.3,
            fill: true,
            yAxisID: 'y'
          },
          {
            label: 'Violations',
            data: data.violations,
            borderColor: '#FF6B4A',
            backgroundColor: 'rgba(255, 107, 74, 0.1)',
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
          legend: { labels: { color: '#6B3A4D', font: { size: 10, weight: 600 } } }
        },
        scales: {
          x: { ticks: { color: '#6B3A4D', font: { size: 9 } }, grid: { display: false } },
          y: { min: 70, max: 100, ticks: { color: '#6B3A4D', font: { size: 9 } }, grid: { color: '#F3D9CF' } },
          y1: { position: 'right', ticks: { color: '#6B3A4D', font: { size: 9 } }, grid: { display: false } }
        }
      }
    });
  } catch (err) {
    console.error('Failed to render Trend chart:', err);
  }
}
