// EoSim Browser Extension — Background Service Worker
// Production API: https://api.eosim.io

const API_BASE = 'https://api.eosim.io';
const APP_URL = 'https://app.eosim.io';
const CHECK_INTERVAL_MINUTES = 5;

// ─── Installation ─────────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    chrome.tabs.create({ url: `${APP_URL}/welcome` });
    chrome.storage.local.set({
      lang: 'en',
      apiBase: API_BASE,
      notifications: true,
      installedAt: new Date().toISOString(),
    });
  }
  setupContextMenu();
  setupAlarms();
});

// ─── Context Menu ─────────────────────────────────────────────────────────────
function setupContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'eosim-open',
      title: 'Open in EoSim',
      contexts: ['page', 'selection'],
    });
    chrome.contextMenus.create({
      id: 'eosim-docs',
      title: 'EoSim Documentation',
      contexts: ['page'],
    });
  });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'eosim-open') {
    chrome.tabs.create({ url: `${APP_URL}/dashboard` });
  } else if (info.menuItemId === 'eosim-docs') {
    chrome.tabs.create({ url: 'https://docs.eosim.io' });
  }
});

// ─── Keyboard Shortcut ────────────────────────────────────────────────────────
chrome.commands.onCommand.addListener((command) => {
  if (command === 'open-eosim') {
    chrome.tabs.create({ url: APP_URL });
  }
});

// ─── Periodic Health Check ────────────────────────────────────────────────────
function setupAlarms() {
  chrome.alarms.create('health-check', { periodInMinutes: CHECK_INTERVAL_MINUTES });
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'health-check') {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/health`, {
        signal: AbortSignal.timeout(5000),
      });
      const data = resp.ok ? await resp.json() : null;
      chrome.storage.local.set({
        lastHealthCheck: new Date().toISOString(),
        apiStatus: resp.ok ? 'online' : 'degraded',
        activeSims: data?.active_simulations ?? 0,
      });
    } catch {
      chrome.storage.local.set({ apiStatus: 'offline' });
    }
  }
});

// ─── Message Handler ──────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_STATUS') {
    chrome.storage.local.get(['apiStatus', 'activeSims', 'lastHealthCheck'], sendResponse);
    return true;
  }
  if (message.type === 'SET_LANG') {
    chrome.storage.local.set({ lang: message.lang });
    sendResponse({ ok: true });
  }
});
