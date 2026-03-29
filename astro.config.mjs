import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://www.elisehasseltine.com',
  base: '/signal-board',
  outDir: './docs',
  integrations: [sitemap()],
  build: {
    format: 'directory',
  },
});
