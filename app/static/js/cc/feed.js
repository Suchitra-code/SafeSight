import { getFeed } from './api.js';

export async function renderLiveFeed() {
  const container = document.getElementById('liveEventsFeed');
  if (!container) return;

  try {
    const data = await getFeed(12);
    const events = data.events || [];

    if (events.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: #64748b; padding: 20px;">No recent camera events.</div>`;
      return;
    }

    container.innerHTML = events.map(e => `
      <div class="feed-item" onclick="window.location.href='/events'">
        <img class="feed-thumb" src="${e.snapshot_url || '/static/img/placeholder_worker.jpg'}" alt="Snap" onerror="this.src='/static/img/placeholder_worker.jpg'">
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <strong style="color: ${e.severity === 'HIGH' ? '#f87171' : '#fcd34d'}; font-size: 11px;">
              ${e.violation_type}
            </strong>
            <span style="font-size: 10px; color: #64748b;">${(e.detected_at || '').slice(11, 19)}</span>
          </div>
          <div style="color: #94a3b8; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${e.camera_name} • ${e.location}
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to render live feed:', err);
  }
}
