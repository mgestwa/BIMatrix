import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    open: false, // Otwiera aplikację w przeglądarce po uruchomieniu
  },
  build: {
    outDir: 'bulid',
  },
});
