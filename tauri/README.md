# Ashu AI Companion - Tauri Desktop App

This is the Tauri desktop wrapper for Ashu AI Companion. It provides a native desktop experience with:

- **System tray** - Ashu lives in your system tray
- **Floating window** - Always-on-top, frameless, transparent window
- **Python bridge** - Auto-starts the NIM cloud bridge on launch
- **Auto-updater** - GitHub Releases integration
- **Single instance** - Only one Ashu runs at a time

## Prerequisites

- **Rust** (latest stable): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Node.js** (18+): Download from nodejs.org
- **Python** (3.11+): Ensure `python` or `python3` is in PATH
- **Tauri CLI**: `cargo install tauri-cli`

## Quick Start

```bash
cd tauri

# Install dependencies
npm install

# Development (hot reload)
npm run dev

# Build for production
npm run build
```

## Project Structure

```
tauri/
├── src/
│   ├── main.rs          # Rust main entry point
│   ├── main.ts          # Frontend entry point
│   ├── style.css        # Desktop-specific styles
│   └── bridge.rs        # Python bridge manager
├── src-tauri/
│   ├── Cargo.toml       # Rust dependencies
│   ├── tauri.conf.json  # Tauri configuration
│   └── icons/           # App icons
├── package.json         # npm config
├── vite.config.ts       # Vite config (serves ../web)
└── tauri.conf.json      # Tauri app config
```

## How It Works

1. **Frontend**: Serves the existing `web/ashu_prototype.html` via Tauri's webview
2. **Bridge Manager** (`bridge.rs`): 
   - Finds Python and `serve.py` automatically
   - Launches `python serve.py --nim --host 127.0.0.1 --port 8765`
   - Monitors health via `/v1/health`
   - Restarts on failure
3. **System Tray**: Shows/hides window, bridge status, quit
4. **Window**: Frameless, transparent, always-on-top, centered

## Configuration

Edit `tauri.conf.json`:
- Update `identifier` to your bundle ID
- Update `updater.endpoints` to your GitHub repo
- Add your updater `pubkey` for signed updates

## Build for Distribution

```bash
npm run build
# Output: src-tauri/target/release/bundle/
# - .msi (Windows)
# - .dmg (macOS)
# - .AppImage/.deb (Linux)
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Python not found" | Ensure `python` or `python3` is in PATH |
| "serve.py not found" | Run from project root, or ensure `serve.py` exists |
| Bridge won't start | Check port 8765 is free, check Python deps |
| Window not showing | Check `visible: false` in tauri.conf.json, app shows after bridge starts |

## Bridge Commands (from frontend)

```typescript
// Check bridge status
const status = await invoke('get_bridge_status')

// Restart bridge
await invoke('restart_bridge')

// Change bridge URL
await invoke('set_bridge_url', { url: 'http://192.168.1.xxx:8765' })
```

## License

MIT (same as main project)