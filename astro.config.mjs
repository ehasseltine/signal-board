import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://www.elisehasseltine.com',
  base: '/signal-board',
  outDir: './docs',
  build: {
    format: 'directory',
  },
});
