/**
 * demo_mode.js — Demo Mode for SafeSight Mission Control.
 *
 * Cycles through a set of pre-canned scenario questions at a fixed interval
 * so a live demo runs hands-free.  Each scenario question is submitted to the
 * Copilot exactly as if the user typed it.
 *
 * Usage:
 *   import { initDemoMode } from './demo_mode.js';
 *   initDemoMode({ sendQueryFn });
 *
 * The "Demo Mode" button (id="demo-mode-btn") toggles the cycle on/off.
 * While active the button shows a countdown to the next question.
 */

'use strict';

// ---------------------------------------------------------------------------
// Demo scenarios
// ---------------------------------------------------------------------------

/** @type {string[]} */
const DEMO_SCENARIOS = [
  'What PPE violations occurred in the last 24 hours?',
  'Which zone has the lowest compliance rate today?',
  'What does the safety manual say about helmet requirements?',
  'Show me a summary of all critical violations this week.',
  'Which cameras detected workers without safety vests?',
  'What is the recommended action for repeat helmet violations?',
  'Compare compliance rates across all zones.',
  'Are there any workers in Zone A without PPE right now?',
];

/** Interval between automatic questions (milliseconds). */
const INTERVAL_MS = 18_000;

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

/** @type {number | null} NodeJS/browser timer handle */
let _timer = null;

/** @type {number} Index of the next scenario to play. */
let _idx = 0;

/** @type {HTMLButtonElement | null} */
let _btn = null;

/** @type {number | null} Countdown display interval */
let _countdownTimer = null;

/** @type {number} Seconds remaining until next question */
let _secondsLeft = 0;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Submit the next scenario and schedule the one after.
 * @param {(q: string) => void} sendQueryFn
 */
function _next(sendQueryFn) {
  const question = DEMO_SCENARIOS[_idx % DEMO_SCENARIOS.length];
  _idx += 1;

  // Fill the visible input.
  const inputEl = document.getElementById('copilot-input');
  if (inputEl) {
    inputEl.value = question;
    inputEl.dispatchEvent(new Event('input'));
  }

  sendQueryFn(question);
  _resetCountdown();
}

/** Reset the countdown display. */
function _resetCountdown() {
  _secondsLeft = Math.round(INTERVAL_MS / 1000);
  _updateBtnLabel();
}

/** Update the button label to show countdown. */
function _updateBtnLabel() {
  if (!_btn) return;
  _btn.textContent = `🎬 Demo ON  (next in ${_secondsLeft}s)`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Initialise demo mode toggle button.
 *
 * @param {{
 *   sendQueryFn: (question: string) => void,
 *   btnId?:      string,
 * }} opts
 */
export function initDemoMode({ sendQueryFn, btnId = 'demo-mode-btn' }) {
  _btn = document.getElementById(btnId);
  if (!_btn) return;

  _btn.addEventListener('click', () => {
    if (_timer !== null) {
      _stopDemo();
    } else {
      _startDemo(sendQueryFn);
    }
  });
}

/**
 * @param {(q: string) => void} sendQueryFn
 */
function _startDemo(sendQueryFn) {
  if (_timer !== null) return;

  // Fire the first question immediately.
  _next(sendQueryFn);

  // Schedule subsequent questions.
  _timer = setInterval(() => _next(sendQueryFn), INTERVAL_MS);

  // Countdown ticker (updates every second).
  _countdownTimer = setInterval(() => {
    _secondsLeft = Math.max(0, _secondsLeft - 1);
    _updateBtnLabel();
  }, 1_000);

  if (_btn) {
    _btn.classList.add('demo-active');
  }
}

function _stopDemo() {
  if (_timer !== null) {
    clearInterval(_timer);
    _timer = null;
  }
  if (_countdownTimer !== null) {
    clearInterval(_countdownTimer);
    _countdownTimer = null;
  }
  if (_btn) {
    _btn.textContent = '🎬 Demo Mode';
    _btn.classList.remove('demo-active');
  }
}

/**
 * Stop demo mode programmatically (e.g. when user starts typing).
 */
export function stopDemoMode() {
  _stopDemo();
}

// Stop demo if the user starts typing manually.
document.addEventListener('keydown', (e) => {
  if (
    _timer !== null &&
    e.target instanceof HTMLInputElement &&
    e.target.id === 'copilot-input'
  ) {
    _stopDemo();
  }
});
