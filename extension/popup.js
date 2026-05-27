// EoSim Browser Extension — Popup Script
// Production API: https://api.eosim.io

const API_BASE = 'https://api.eosim.io';
const APP_URL = 'https://app.eosim.io';
const DOCS_URL = 'https://docs.eosim.io';
const METRICS_URL = 'https://metrics.eosim.io';

let currentLang = 'en';

// ─── Tab Navigation ───────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.remove('hidden');
  event.target.classList.add('active');
  if (name === 'metrics') loadMetrics();
}

// ─── Simulation Actions ───────────────────────────────────────────────────────
function launchSim(type) {
  chrome.tabs.create({ url: `${APP_URL}/simulations/new?type=${type}` });
  window.close();
}

function openDashboard() {
  chrome.tabs.create({ url: `${APP_URL}/dashboard` });
  window.close();
}

function newSim() {
  chrome.tabs.create({ url: `${APP_URL}/simulations/new` });
  window.close();
}

function openApp() {
  chrome.tabs.create({ url: APP_URL });
  window.close();
}

function openMetrics() {
  chrome.tabs.create({ url: METRICS_URL });
  window.close();
}

// ─── Metrics Loading ──────────────────────────────────────────────────────────
async function loadMetrics() {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) {
      const data = await resp.json();
      const el = document.getElementById('activeSims');
      if (el) el.textContent = data.active_simulations ?? data.activeSimulations ?? '—';
      document.getElementById('statusDot').style.background = '#34d399';
    }
  } catch {
    document.getElementById('statusDot').style.background = '#f87171';
  }
}

// ─── Language Selection ───────────────────────────────────────────────────────
function setLang(code, name) {
  currentLang = code;
  document.getElementById('selectedLang').textContent = name;
  document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  chrome.storage.local.set({ lang: code });
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chrome.storage.local.get(['lang'], (result) => {
    if (result.lang) {
      currentLang = result.lang;
    }
  });
  loadMetrics();
});
