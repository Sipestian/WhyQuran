import { defineConfig } from 'astro/config';
import { prepareResearchReports } from './scripts/research-validation.mjs';
import { siteOrigin } from './src/lib/site.mjs';

export default defineConfig({
  site: siteOrigin,
  integrations: [{
    name: 'verified-research',
    hooks: {
      'astro:build:start': ({ logger }) => {
        prepareResearchReports(process.cwd());
        logger.info('Canonical research validation passed; make reports regenerated the research reports.');
      },
    },
  }],
  output: 'static',
  // Keep each checkout's content and optimizer caches outside shared dependencies.
  cacheDir: './.astro/cache/',
  vite: { cacheDir: './.astro/vite/' },
  trailingSlash: 'always',
  devToolbar: { enabled: false },
  build: { format: 'directory' },
});
