import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://signal-board.org',
  base: '/',
  outDir: './docs',
  integrations: [sitemap()],
  build: {
    format: 'directory',
  },
});
