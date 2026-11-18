import { store } from './store.js';
import { getHeatmap } from './api.js';

export async function renderHeatmap() {
  const container = document.getElementById('heatmapContainer');
  if (!container) return;

  try {
    const data = await getHeatmap(store.filters);
    const matrix = data.matrix || [];

    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    let html = `<div style="display: grid; grid-template-columns: 35px repeat(24, 1fr); gap: 2px; font-size: 9px; align-items: center;">`;
    html += `<div></div>`;
    for (let h = 0; h < 24; h += 3) {
      html += `<div style="grid-column: span 3; text-align: center; color: #64748b;">${h}:00</div>`;
    }

    days.forEach(day => {
      html += `<div style="font-weight: 700; color: #94a3b8;">${day}</div>`;
      for (let h = 0; h < 24; h++) {
        const item = matrix.find(m => m.day === day && m.hour === h) || { count: 0 };
        const opacity = Math.min(1.0, item.count * 0.35 + 0.08);
        const col = item.count > 0 ? `rgba(245, 158, 11, ${opacity})` : 'rgba(30, 41, 59, 0.4)';
        html += `<div style="height: 12px; background: ${col}; border-radius: 2px;" title="${day} ${h}:00 - ${item.count} violation(s)"></div>`;
      }
    });

    html += `</div>`;
    container.innerHTML = html;
  } catch (err) {
    console.error('Failed to render Heatmap:', err);
  }
}
