import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://ehasseltine.github.io',
  base: '/signal-board',
  outDir: './docs',
  build: {
    format: 'directory',
  },
});
