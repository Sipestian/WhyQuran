import { defineConfig } from 'astro/config';
import { prepareResearchReports } from './scripts/research-validation.mjs';

export default defineConfig({
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
