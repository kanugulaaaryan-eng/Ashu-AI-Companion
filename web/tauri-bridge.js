// Tauri Bridge for Ashu Web App
// This script adds Tauri API support to the existing web app

(function() {
  'use strict';

  // Wait for Tauri APIs to be available
  function waitForTauri(maxAttempts = 50) {
    return new Promise((resolve) => {
      let attempts = 0;
      const check = () => {
        if (window.__TAURI_INVOKE__ || window.__TAURI__) {
          resolve();
        } else if (attempts >= maxAttempts) {
          console.warn('Tauri APIs not available after', maxAttempts, 'attempts');
          resolve(); // Continue anyway
        } else {
          attempts++;
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  // Initialize Tauri integration
  async function initTauri() {
    await waitForTauri();

    if (!window.__TAURI_INVOKE__ && !window.__TAURI__) {
      console.log('Running in browser mode (no Tauri)');
      return;
    }

    console.log('Tauri APIs available, initializing bridge...');

    // Patch the bridge URL to use localhost
    const originalFetch = window.fetch;
    window.fetch = async function(input, init) {
      if (typeof input === 'string' && input.startsWith('/v1/')) {
        // Rewrite API calls to use the local bridge
        const url = 'http://127.0.0.1:8765' + input;
        return originalFetch.call(this, url, init);
      }
      return originalFetch.call(this, input, init);
    };

    // Add window controls support
    window.minimizeWindow = async () => {
      try {
        if (window.__TAURI_INVOKE__) {
          await window.__TAURI_INVOKE__('minimize_window');
        }
      } catch (e) {
        console.warn('Minimize failed:', e);
      }
    };

    window.hideWindow = async () => {
      try {
        if (window.__TAURI_INVOKE__) {
          await window.__TAURI_INVOKE__('hide_window');
        }
      } catch (e) {
        console.warn('Hide failed:', e);
      }
    };

    window.restartBridge = async () => {
      try {
        if (window.__TAURI_INVOKE__) {
          await window.__TAURI_INVOKE__('restart_bridge');
        }
      } catch (e) {
        console.warn('Restart bridge failed:', e);
      }
    };

    // Listen for bridge status updates
    if (window.__TAURI__) {
      const { listen } = window.__TAURI__.event;
      await listen('bridge-status', (event) => {
        const status = event.payload;
        console.log('Bridge status:', status);
        // Dispatch custom event for the app to handle
        window.dispatchEvent(new CustomEvent('ashu-bridge-status', { detail: status }));
      });
    }

    console.log('Tauri bridge initialized');
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTauri);
  } else {
    initTauri();
  }

  // Expose for manual init
  window.AshuTauriBridge = { initTauri };
})();