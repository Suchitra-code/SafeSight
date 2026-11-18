import { store } from './store.js';
import { getZones } from './api.js';

export async function initSiteMap() {
  const container = document.getElementById('sitemapContainer');
  if (!container) return;

  try {
    const res = await fetch('/static/data/site_map.json');
    const mapData = await res.json();
    const zoneStats = await getZones();
    const stats = zoneStats.zones || {};

    const svgWidth = mapData.dimensions.width;
    const svgHeight = mapData.dimensions.height;

    let svgHtml = `
      <svg viewBox="0 0 ${svgWidth} ${svgHeight}" style="width: 100%; height: auto; border-radius: 8px; background: #0b1120;">
        <defs>
          <pattern id="gridPattern" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1e293b" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="${svgWidth}" height="${svgHeight}" fill="url(#gridPattern)" />
    `;

    mapData.zones.forEach(z => {
      const s = stats[z.name] || { compliance: 95, violations: 0 };
      const isSelected = store.filters.zone === z.name;
      const strokeCol = isSelected ? '#3b82f6' : (s.compliance < 85 ? '#ef4444' : '#64748b');

      svgHtml += `
        <polygon id="poly_${z.id}" points="${z.polygon}" class="sitemap-zone ${s.compliance < 85 ? 'zone-high-risk' : ''}" 
                 data-zone="${z.name}" stroke="${strokeCol}" stroke-width="${isSelected ? 3 : 1.5}">
          <title>${z.label}\nCompliance: ${s.compliance}%\nViolations: ${s.violations}</title>
        </polygon>
        <text x="${z.center[0]}" y="${z.center[1]}" fill="#f8fafc" font-size="12" font-weight="700" text-anchor="middle" pointer-events="none">
          ${z.name} (${s.compliance}%)
        </text>
      `;

      // Render camera icons
      z.cameras.forEach(cam => {
        svgHtml += `
          <circle cx="${cam.coords[0]}" cy="${cam.coords[1]}" r="6" fill="#38bdf8" stroke="#0f172a" stroke-width="2">
            <title>${cam.name} (${cam.type})</title>
          </circle>
        `;
      });
    });

    svgHtml += `</svg>`;
    container.innerHTML = svgHtml;

    // Attach click events to zones
    container.querySelectorAll('.sitemap-zone').forEach(poly => {
      poly.addEventListener('click', (e) => {
        const zoneName = e.target.dataset.zone;
        if (store.filters.zone === zoneName) {
          store.setFilter('zone', null);
        } else {
          store.setFilter('zone', zoneName);
        }
      });
    });

  } catch (err) {
    console.error('Failed to initialize Site Map:', err);
  }
}
