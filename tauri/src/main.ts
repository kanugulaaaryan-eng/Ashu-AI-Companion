// Tauri entry point - loads the existing web PWA
import './style.css'

// Initialize Tauri APIs
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'

// Bridge status monitoring
let bridgeStatusCheckInterval: number | null = null

async function checkBridgeStatus() {
  try {
    const status = await invoke('get_bridge_status')
    updateBridgeUI(status)
  } catch (e) {
    console.warn('Bridge status check failed:', e)
  }
}

function updateBridgeUI(status: any) {
  const indicator = document.getElementById('bridge-status')
  if (!indicator) return

  if (status.running) {
    indicator.className = 'bridge-status running'
    indicator.textContent = `🟢 Bridge: ${status.model} (${status.url})`
  } else {
    indicator.className = 'bridge-status stopped'
    indicator.textContent = `🔴 Bridge: ${status.error || 'Stopped'}`
  }
}

// Start monitoring when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  checkBridgeStatus()
  bridgeStatusCheckInterval = window.setInterval(checkBridgeStatus, 10000)

  // Listen for bridge status events from Rust
  listen('bridge-status', (event) => {
    updateBridgeUI(event.payload)
  })

  // Handle window controls
  const minimizeBtn = document.getElementById('minimize-btn')
  const closeBtn = document.getElementById('close-btn')
  const restartBridgeBtn = document.getElementById('restart-bridge-btn')

  if (minimizeBtn) {
    minimizeBtn.addEventListener('click', () => {
      invoke('minimize_window')
    })
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      invoke('hide_window')
    })
  }

  if (restartBridgeBtn) {
    restartBridgeBtn.addEventListener('click', async () => {
      try {
        await invoke('restart_bridge')
        checkBridgeStatus()
      } catch (e) {
        console.error('Restart failed:', e)
      }
    })
  }
})

// Cleanup on unload
window.addEventListener('beforeunload', () => {
  if (bridgeStatusCheckInterval) {
    clearInterval(bridgeStatusCheckInterval)
  }
})

// Expose Tauri invoke for the existing web app
declare global {
  interface Window {
    __TAURI_INVOKE__: typeof invoke
  }
}
window.__TAURI_INVOKE__ = invoke