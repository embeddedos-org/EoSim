// EoSim Browser Extension — Content Script
// Enhances EoSim web app pages with extension features

(function() {
  'use strict';

  // Only run on EoSim domains
  const EOSIM_DOMAINS = ['eosim.io', 'app.eosim.io', 'api.eosim.io'];
  const isEoSimPage = EOSIM_DOMAINS.some(d => window.location.hostname.includes(d));
  if (!isEoSimPage) return;

  // Inject extension indicator
  const indicator = document.createElement('div');
  indicator.id = 'eosim-ext-indicator';
  indicator.style.cssText = `
    position: fixed; bottom: 16px; right: 16px; z-index: 99999;
    background: rgba(10,14,26,0.9); border: 1px solid #334155;
    border-radius: 8px; padding: 6px 10px; font-size: 11px;
    color: #60a5fa; font-family: -apple-system, sans-serif;
    pointer-events: none; backdrop-filter: blur(8px);
  `;
  indicator.textContent = '⚡ EoSim Extension Active';
  document.body?.appendChild(indicator);
  setTimeout(() => indicator.remove(), 3000);

  // Listen for messages from background
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'LANG_CHANGED') {
      document.documentElement.lang = message.lang;
    }
  });

  // Notify background that EoSim page is active
  chrome.runtime.sendMessage({ type: 'PAGE_ACTIVE', url: window.location.href });
})();
