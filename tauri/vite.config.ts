import { defineConfig } from 'vite'
import path from 'path'
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from 'fs'

export default defineConfig({
  root: path.resolve(__dirname, '..', 'web'),
  publicDir: path.resolve(__dirname, '..', 'web'),
  build: {
    outDir: path.resolve(__dirname, 'src-tauri', 'web-dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, '..', 'web', 'ashu_prototype.html'),
        companion: path.resolve(__dirname, '..', 'web', 'ashu_companion.html')
      }
    }
  },
  plugins: [
    {
      name: 'copy-assets',
      closeBundle() {
        const srcDir = path.resolve(__dirname, '..', 'web');
        const destDir = path.resolve(__dirname, 'src-tauri', 'web-dist');
        
        // Copy all web assets (images, fonts, etc.)
        const assetsDir = path.join(srcDir, 'assets');
        if (existsSync(assetsDir)) {
          copyDir(assetsDir, path.join(destDir, 'assets'));
        }
        
        // Copy other static files
        const staticFiles = ['favicon.svg', 'manifest.webmanifest', 'sw.js', 'icon-192.png', 'icon-512.png', 'tauri-bridge.js'];
        for (const file of staticFiles) {
          const src = path.join(srcDir, file);
          const dest = path.join(destDir, file);
          if (existsSync(src)) {
            copyFileSync(src, dest);
          }
        }
      }
    }
  ],
  server: {
    port: 1420,
    strictPort: true,
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 1421
    }
  }
})

function copyDir(src, dest) {
  if (!existsSync(dest)) {
    mkdirSync(dest, { recursive: true });
  }
  const entries = readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      copyFileSync(srcPath, destPath);
    }
  }
}