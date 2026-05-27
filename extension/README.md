# EoSim Browser Extension

A Manifest V3 browser extension for Chrome, Edge, Firefox, and other Chromium-based browsers.

## Features

- Quick access to all 20 simulation modules
- Real-time metrics from the production API (`api.eosim.io`)
- 10-language interface (EN, ES, ZH, HI, FR, AR, PT, DE, JA, KO)
- Context menu integration
- Keyboard shortcut: `Ctrl+Shift+E` (Mac: `Cmd+Shift+E`)
- Periodic health checks with notifications
- Settings page for API key configuration

## Installation (Development)

1. Open Chrome and navigate to `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` directory

## Production Release

The extension is published to:
- [Chrome Web Store](https://chrome.google.com/webstore)
- [Microsoft Edge Add-ons](https://microsoftedge.microsoft.com/addons)
- [Firefox Add-ons (AMO)](https://addons.mozilla.org) — requires manifest v2 compatibility layer

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest (MV3) |
| `popup.html` / `popup.js` | Main popup UI |
| `background.js` | Service worker for background tasks |
| `content.js` | Content script injected into EoSim pages |
| `options.html` | Settings/options page |
