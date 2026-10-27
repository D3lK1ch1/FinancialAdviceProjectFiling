import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// One self-contained HTML file, dist/index.html, which FastAPI serves at /.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: { outDir: 'dist', assetsInlineLimit: 100000000 },
  // `npm run dev` talks to the Python backend (uvicorn on port 8000).
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/review': 'http://127.0.0.1:8000' } },
});
