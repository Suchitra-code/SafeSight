import { getGraphMeta } from './api.js';

let cachedNodes = [];

export async function initPipelineViz() {
  const container = document.getElementById('pipelineNodesRow');
  if (!container) return;

  try {
    const meta = await getGraphMeta();
    cachedNodes = meta.nodes.filter(n => [1, 2, 3, 4, 5, 6, 7].includes(n.step));
    cachedNodes.sort((a, b) => a.step - b.step);

    container.innerHTML = cachedNodes.map(n => `
      <div id="pnode_${n.id}" class="pipeline-node" title="${n.description}">
        <span class="pnode-dot" style="width: 6px; height: 6px; border-radius: 50%; background: #64748b;"></span>
        <span>${n.label}</span>
      </div>
    `).join('<span style="color: #334155; font-size: 10px;">➔</span>');
  } catch (err) {
    console.error('Failed to init pipeline viz:', err);
  }
}

export function setNodeActive(nodeName) {
  cachedNodes.forEach(n => {
    const el = document.getElementById(`pnode_${n.id}`);
    if (el) {
      if (n.id === nodeName) {
        el.className = 'pipeline-node active';
      } else if (el.classList.contains('active')) {
        el.className = 'pipeline-node completed';
      }
    }
  });
}

export function setNodeCompleted(nodeName) {
  const el = document.getElementById(`pnode_${nodeName}`);
  if (el) {
    el.className = 'pipeline-node completed';
  }
}

export function resetPipelineViz() {
  cachedNodes.forEach(n => {
    const el = document.getElementById(`pnode_${n.id}`);
    if (el) el.className = 'pipeline-node';
  });
}
