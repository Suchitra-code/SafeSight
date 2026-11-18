/**
 * voice.js — Web Speech API integration for SafeSight Mission Control.
 *
 * Features (all feature-detected with graceful fallbacks):
 *   • Voice input  : Click the mic button → speak your query → auto-submit.
 *   • Speech output: Copilot answer summary is read aloud when enabled.
 *   • Language     : Defaults to 'en-US'.  Respects <html lang> if set.
 *
 * Usage:
 *   import { initVoice, speakText, stopSpeech } from './voice.js';
 *   initVoice({
 *     inputEl:  document.getElementById('copilot-input'),
 *     micBtn:   document.getElementById('mic-btn'),
 *     submitFn: (text) => sendCopilotQuery(text),
 *   });
 *
 * No external dependencies.  Silently does nothing if the browser doesn't
 * support the Web Speech API.
 */

'use strict';

// ---------------------------------------------------------------------------
// Feature detection
// ---------------------------------------------------------------------------

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

const synth = window.speechSynthesis || null;

/** True when the browser supports voice input. */
export const canListen = Boolean(SpeechRecognition);

/** True when the browser supports speech output. */
export const canSpeak = Boolean(synth);

// ---------------------------------------------------------------------------
// Module state
// ---------------------------------------------------------------------------

/** @type {SpeechRecognition | null} */
let _recognition = null;

/** @type {boolean} */
let _listening = false;

/** @type {boolean}  Whether speech output is globally enabled by the user. */
let _speechEnabled = false;

// ---------------------------------------------------------------------------
// Voice Input
// ---------------------------------------------------------------------------

/**
 * Initialise voice input.
 *
 * @param {{
 *   inputEl:  HTMLInputElement,
 *   micBtn:   HTMLButtonElement,
 *   submitFn: (text: string) => void,
 * }} opts
 */
export function initVoice({ inputEl, micBtn, submitFn }) {
  if (!canListen) {
    if (micBtn) {
      micBtn.title = 'Voice input not supported in this browser';
      micBtn.disabled = true;
      micBtn.style.opacity = '0.4';
    }
    return;
  }

  micBtn?.addEventListener('click', () => {
    if (_listening) {
      _stopListening(micBtn);
    } else {
      _startListening(inputEl, micBtn, submitFn);
    }
  });
}

/**
 * @param {HTMLInputElement}  inputEl
 * @param {HTMLButtonElement} micBtn
 * @param {(text: string) => void} submitFn
 */
function _startListening(inputEl, micBtn, submitFn) {
  _recognition = new SpeechRecognition();
  _recognition.lang = document.documentElement.lang || 'en-US';
  _recognition.interimResults = true;
  _recognition.maxAlternatives = 1;
  _recognition.continuous = false;

  _listening = true;
  _setMicState(micBtn, true);

  _recognition.onresult = (event) => {
    let interimTranscript = '';
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    if (inputEl) {
      inputEl.value = finalTranscript || interimTranscript;
      inputEl.dispatchEvent(new Event('input'));
    }

    if (finalTranscript.trim()) {
      _stopListening(micBtn);
      submitFn?.(finalTranscript.trim());
    }
  };

  _recognition.onerror = (event) => {
    console.warn('[voice] recognition error:', event.error);
    _stopListening(micBtn);
    _showToast(
      event.error === 'not-allowed'
        ? 'Microphone permission denied. Enable it in browser settings.'
        : `Voice error: ${event.error}`
    );
  };

  _recognition.onend = () => {
    _listening = false;
    _setMicState(micBtn, false);
  };

  try {
    _recognition.start();
  } catch (err) {
    console.warn('[voice] could not start recognition:', err);
    _listening = false;
    _setMicState(micBtn, false);
  }
}

/** @param {HTMLButtonElement} micBtn */
function _stopListening(micBtn) {
  _listening = false;
  _setMicState(micBtn, false);
  try {
    _recognition?.stop();
  } catch (_) {
    /* ignore */
  }
  _recognition = null;
}

/**
 * Update mic button visual state.
 * @param {HTMLButtonElement|null} btn
 * @param {boolean} active
 */
function _setMicState(btn, active) {
  if (!btn) return;
  btn.classList.toggle('mic-active', active);
  btn.title = active ? 'Stop listening (click to cancel)' : 'Voice input';
  btn.setAttribute('aria-pressed', String(active));
}

// ---------------------------------------------------------------------------
// Speech Output
// ---------------------------------------------------------------------------

/**
 * Enable or disable speech output globally.
 * @param {boolean} enabled
 */
export function setSpeechEnabled(enabled) {
  _speechEnabled = enabled;
  if (!enabled) stopSpeech();
}

/**
 * Speak a text string aloud (if speech is enabled and supported).
 * Long texts are truncated to 500 characters to keep it snappy.
 *
 * @param {string} text
 * @param {{ rate?: number, pitch?: number, volume?: number }} [opts]
 */
export function speakText(text, opts = {}) {
  if (!canSpeak || !_speechEnabled) return;
  stopSpeech(); // cancel any ongoing speech first

  const utter = new SpeechSynthesisUtterance(
    text.length > 500 ? text.slice(0, 500) + '…' : text
  );
  utter.lang   = document.documentElement.lang || 'en-US';
  utter.rate   = opts.rate   ?? 1.0;
  utter.pitch  = opts.pitch  ?? 1.0;
  utter.volume = opts.volume ?? 1.0;

  utter.onerror = (e) => {
    // SpeechSynthesisErrorEvent — silence is acceptable here
    if (e.error !== 'interrupted') {
      console.warn('[voice] speech synthesis error:', e.error);
    }
  };

  synth.speak(utter);
}

/** Cancel any ongoing speech synthesis. */
export function stopSpeech() {
  if (canSpeak) {
    try {
      synth.cancel();
    } catch (_) {
      /* ignore */
    }
  }
}

// ---------------------------------------------------------------------------
// Internal toast helper (no external dependency)
// ---------------------------------------------------------------------------

/** @param {string} message */
function _showToast(message) {
  // Re-use an existing toast container if one exists on the page.
  let container = document.getElementById('cc-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'cc-toast-container';
    container.style.cssText =
      'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.cssText =
    'background:#FFFFFF;color:#4A1D2F;border:1.5px solid #FF6B4A;border-radius:.5rem;' +
    'padding:.6rem 1rem;font-size:.85rem;max-width:280px;box-shadow:0 8px 24px rgba(255,107,74,0.15);';
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity .4s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}
