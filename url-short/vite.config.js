import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/shorten': 'http://localhost:5000',
      '/register': 'http://localhost:5000',
      '/login': 'http://localhost:5000',
      '/logout': 'http://localhost:5000',
      '/my-urls': 'http://localhost:5000',
      '/qr': 'http://localhost:5000',
      '/delete': 'http://localhost:5000',
    },
  },
})
