/**
 * ui.js — SafeSight AI "Sunrise Garden" UI/UX Engine (Milestone 5)
 * 
 * Features:
 * - Number count-up animations for KPI cards
 * - Toast notification system (Sunrise Garden palette)
 * - Confetti particle burst on compliance/investigation resolve
 * - Global Command Palette (Ctrl+K)
 * - Guided first-run tour with local storage memory
 * - Universal Chart.js & Plotly palette enforcer (strictly NO blue!)
 */

'use strict';

// ── Palette Constants (strictly NO blue / NO black) ──
export const PALETTE = {
  coral: '#FF6B4A',
  orange: '#FF9F1C',
  sun: '#FFC93C',
  lime: '#8CC63F',
  mint: '#22B573',
  pink: '#FF4D8D',
  magenta: '#D6247F',
  berry: '#B5179E',
  red: '#E53950',
  textStrong: '#4A1D2F',
  textMain: '#6B3A4D',
  textSoft: '#9A6B7E',
  bgCard: '#FFFFFF',
  bgPage: '#FFF7EE',
  border: '#F3D9CF',
  chartColors: [
    '#FF6B4A', // coral
    '#FFC93C', // sun
    '#FF4D8D', // pink
    '#22B573', // mint
    '#FF9F1C', // orange
    '#B5179E', // berry
    '#8CC63F', // lime
    '#D6247F', // magenta
    '#E53950'  // red
  ]
};

// ── 1. Global Chart.js Configuration ──
if (window.Chart) {
  Chart.defaults.color = PALETTE.textMain;
  Chart.defaults.borderColor = PALETTE.border;
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = '#FFFFFF';
  Chart.defaults.plugins.tooltip.titleColor = PALETTE.textStrong;
  Chart.defaults.plugins.tooltip.bodyColor = PALETTE.textMain;
  Chart.defaults.plugins.tooltip.borderColor = PALETTE.border;
  Chart.defaults.plugins.tooltip.borderWidth = 1.5;
  Chart.defaults.plugins.tooltip.boxPadding = 6;
  Chart.defaults.plugins.tooltip.usePointStyle = true;
}

// ── 2. Number Count-Up Animation ──
export function animateCountUp(element, targetVal, durationMs = 900, suffix = '', prefix = '') {
  if (!element) return;
  const target = parseFloat(targetVal);
  if (isNaN(target)) {
    element.textContent = prefix + targetVal + suffix;
    return;
  }
  const isFloat = String(targetVal).includes('.');
  const decimals = isFloat ? String(targetVal).split('.')[1].length : 0;
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / durationMs, 1);
    // ease-out cubic
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const current = start + (target - start) * easeProgress;
    element.textContent = prefix + current.toFixed(decimals) + suffix;

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = prefix + target.toFixed(decimals) + suffix;
    }
  }
  requestAnimationFrame(update);
}

// ── 3. Toast Notifications ──
export function showToast(message, type = 'info', durationMs = 4000) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }

  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: '🌸'
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span style="font-size: 1.1rem;">${icons[type] || '🌸'}</span>
    <span style="color: var(--text-strong);">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'all 0.35s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 350);
  }, durationMs);
}

// Attach globally for legacy templates
window.showToast = showToast;

// ── 4. Confetti Burst Particle Generator ──
export function triggerConfetti() {
  let canvas = document.getElementById('confettiCanvas');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'confettiCanvas';
    document.body.appendChild(canvas);
  }
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const count = 75;
  const colors = PALETTE.chartColors;

  for (let i = 0; i < count; i++) {
    particles.push({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
      r: Math.random() * 6 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      vx: (Math.random() - 0.5) * 16,
      vy: (Math.random() - 0.5) * 16 - 3,
      gravity: 0.35,
      alpha: 1,
      decay: Math.random() * 0.015 + 0.01
    });
  }

  function frame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let active = 0;
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += p.gravity;
      p.alpha -= p.decay;

      if (p.alpha > 0) {
        active++;
        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    });

    if (active > 0) {
      requestAnimationFrame(frame);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
  requestAnimationFrame(frame);
}

// ── 5. Global Command Palette (Ctrl+K) ──
export function initCommandPalette() {
  if (document.getElementById('cmdPaletteModal')) return;

  const modal = document.createElement('div');
  modal.id = 'cmdPaletteModal';
  modal.style.cssText = `
    position: fixed; inset: 0; background: rgba(74, 29, 47, 0.4);
    display: none; align-items: flex-start; justify-content: center;
    padding-top: 15vh; z-index: 99999; backdrop-filter: blur(4px);
  `;

  modal.innerHTML = `
    <div style="background: #FFFFFF; width: 560px; max-width: 90vw; border-radius: 20px; box-shadow: 0 20px 50px rgba(214, 36, 127, 0.25); border: 2px solid #F3D9CF; overflow: hidden; animation: fadeInUp 0.25s ease;">
      <div style="padding: 16px 20px; border-bottom: 1.5px solid #F3D9CF; display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 1.25rem;">🔍</span>
        <input id="cmdPaletteInput" type="text" placeholder="Jump to page or run command... (Esc to close)" style="width: 100%; border: none; font-size: 1.05rem; font-family: 'Poppins', sans-serif; font-weight: 600; color: #4A1D2F; outline: none; background: transparent;">
      </div>
      <div id="cmdPaletteList" style="max-height: 340px; overflow-y: auto; padding: 10px;">
        <!-- Filled dynamically -->
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const commands = [
    { label: '🛡️ Mission Control (M4 Live Dashboard)', url: '/command-center' },
    { label: '📊 BI Analytics Dashboard', url: '/dashboard' },
    { label: '📹 Live Multi-Camera Monitor', url: '/live' },
    { label: '📤 Upload Media / Image / Video', url: '/upload' },
    { label: '📋 Violation Events & Audit Log', url: '/events' },
    { label: '🔍 AI Safety Investigations (LangGraph)', url: '/investigations' },
    { label: '🤖 AI Safety Assistant (RAG)', url: '/assistant' },
    { label: '📂 Documents Library & OCR', url: '/documents' },
    { label: '🧠 Searchable Knowledge Base', url: '/knowledge' },
    { label: '📑 Safety Compliance PDF Reports', url: '/reports' },
    { label: '🏥 System Operational Health Card', url: '/api/health' }
  ];

  const input = modal.querySelector('#cmdPaletteInput');
  const list = modal.querySelector('#cmdPaletteList');

  function renderList(query = '') {
    const q = query.toLowerCase().trim();
    const filtered = commands.filter(c => c.label.toLowerCase().includes(q));
    if (filtered.length === 0) {
      list.innerHTML = `<div style="padding: 16px; text-align: center; color: #9A6B7E;">No matching pages found</div>`;
      return;
    }
    list.innerHTML = filtered.map((c, i) => `
      <div class="cmd-item" data-url="${c.url}" style="padding: 10px 14px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; font-weight: 600; font-size: 0.9rem; color: #4A1D2F; transition: all 0.15s ease; ${i === 0 ? 'background: #FFE3D3;' : ''}">
        <span>${c.label}</span>
        <span style="font-size: 0.75rem; color: #FF6B4A; background: #FFF7EE; padding: 2px 8px; border-radius: 999px;">Jump ↵</span>
      </div>
    `).join('');

    list.querySelectorAll('.cmd-item').forEach(item => {
      item.addEventListener('mouseenter', () => {
        list.querySelectorAll('.cmd-item').forEach(el => el.style.background = 'transparent');
        item.style.background = '#FFE3D3';
      });
      item.addEventListener('click', () => {
        window.location.href = item.dataset.url;
      });
    });
  }

  function openPalette() {
    modal.style.display = 'flex';
    input.value = '';
    renderList();
    input.focus();
  }

  function closePalette() {
    modal.style.display = 'none';
  }

  input.addEventListener('input', (e) => renderList(e.target.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePalette();
    if (e.key === 'Enter') {
      const active = list.querySelector('.cmd-item');
      if (active) window.location.href = active.dataset.url;
    }
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closePalette();
  });

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      modal.style.display === 'flex' ? closePalette() : openPalette();
    }
  });
}

// ── 6. Guided First-Run Tour ──
export function initFirstRunTour() {
  if (localStorage.getItem('safesight_tour_done')) return;

  const steps = [
    { title: 'Welcome to SafeSight AI 🌸', text: 'AI-powered worker safety intelligence platform. Let us show you around!' },
    { title: '🛡️ Mission Control', text: 'Real-time telemetry, interactive 3D site map, and the LangGraph Copilot STAR.' },
    { title: '🔍 LangGraph Investigations', text: 'Automated 10-node AI incident reviews with evidence validation & human approval.' },
    { title: '⌨️ Quick Navigation', text: 'Press Ctrl+K anywhere to jump instantly between dashboards and workflows.' }
  ];

  let currentStep = 0;
  const tourModal = document.createElement('div');
  tourModal.id = 'safesightTourModal';
  tourModal.style.cssText = `
    position: fixed; bottom: 30px; left: 30px; z-index: 99998;
    background: #FFFFFF; border-radius: 20px; padding: 22px 26px;
    box-shadow: 0 16px 40px rgba(214, 36, 127, 0.25); border: 2px solid #FF6B4A;
    max-width: 360px; animation: fadeInUp 0.4s ease;
  `;

  function renderStep() {
    const s = steps[currentStep];
    tourModal.innerHTML = `
      <div style="font-family: 'Poppins', sans-serif; font-weight: 700; color: #4A1D2F; font-size: 1.05rem; margin-bottom: 6px;">
        ${s.title}
      </div>
      <p style="font-size: 0.85rem; color: #6B3A4D; line-height: 1.5; margin-bottom: 16px;">
        ${s.text}
      </p>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.75rem; font-weight: 700; color: #FF6B4A;">${currentStep + 1} of ${steps.length}</span>
        <div style="display: flex; gap: 8px;">
          <button id="tourSkipBtn" class="btn btn-ghost btn-sm" style="font-size: 0.75rem; padding: 4px 10px;">Skip</button>
          <button id="tourNextBtn" class="btn btn-primary btn-sm" style="font-size: 0.75rem; padding: 4px 14px;">${currentStep === steps.length - 1 ? 'Finish 🎉' : 'Next →'}</button>
        </div>
      </div>
    `;

    tourModal.querySelector('#tourSkipBtn').onclick = finishTour;
    tourModal.querySelector('#tourNextBtn').onclick = () => {
      if (currentStep < steps.length - 1) {
        currentStep++;
        renderStep();
      } else {
        finishTour();
      }
    };
  }

  function finishTour() {
    localStorage.setItem('safesight_tour_done', 'true');
    tourModal.remove();
    triggerConfetti();
  }

  document.body.appendChild(tourModal);
  renderStep();
}

// ── Auto-initialize on DOM ready ──
document.addEventListener('DOMContentLoaded', () => {
  initCommandPalette();
  initFirstRunTour();
});
