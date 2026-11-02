import { readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { validateRelease } from './release-coverage.mjs';
import { siteOrigin } from '../src/lib/site.mjs';
const dist = resolve(process.argv[2] ?? 'dist');
const report = JSON.parse(readFileSync(join(dist, 'release.json'), 'utf8'));
const result = validateRelease(report);
const sitemap = readFileSync(join(dist, 'sitemap.xml'), 'utf8');
const robots = readFileSync(join(dist, 'robots.txt'), 'utf8');
if (!robots.includes(`Sitemap: ${siteOrigin}/sitemap.xml`) || robots.includes('Disallow: /')) {
  throw new Error('Production robots configuration is missing or blocks the release');
}
for (const { article_slug: slug } of report.entries) {
  const path = join(dist, 'articles', slug, 'index.html');
  if (!existsSync(path)) throw new Error(`Missing release route: ${slug}`);
  const html = readFileSync(path, 'utf8');
  const canonical = `${siteOrigin}/articles/${slug}/`;
  if (!html.includes(`rel="canonical" href="${canonical}"`) || !sitemap.includes(`<loc>${canonical}</loc>`)) {
    throw new Error(`Missing canonical or sitemap entry: ${slug}`);
  }
  if (/name="robots"[^>]*noindex/.test(html)) throw new Error(`Release article is noindex: ${slug}`);
}
console.log(`First release verified: ${result.topics} reviewed topics, ${result.articles} published articles, canonical URLs and sitemap present.`);
