import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// On GitHub Pages the app is served under /uniqa-conversion-coach/; locally under /.
export default defineConfig({
  plugins: [react()],
  base: process.env.GITHUB_ACTIONS ? '/uniqa-conversion-coach/' : '/',
  server: { port: 5180, open: true },
})
