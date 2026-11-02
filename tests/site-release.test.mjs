import test from 'node:test';
import assert from 'node:assert/strict';
import { validateRelease } from '../scripts/release-coverage.mjs';
import { sitemapXML, robotsText, siteOrigin } from '../src/lib/site.mjs';

const fixture = () => ({
  topics: [{ id: 'one', status: 'reviewed', article_slug: 'sample', evidence_ids: ['evidence'] }],
  entries: [{ topic_id: 'one', article_slug: 'sample' }],
  articles: [{ id: 'sample', draft: false, evidence_ids: ['evidence'] }],
});
test('release requires a reviewed published assessment for every registered topic', () => {
  assert.doesNotThrow(() => validateRelease(fixture()));
  for (const alter of [
    f => f.entries.pop(),
    f => f.entries.push(f.entries[0]),
    f => f.entries.push({ topic_id: 'unknown', article_slug: 'sample' }),
    f => f.topics[0].status = 'draft',
    f => f.articles[0].draft = true,
    f => f.entries[0].article_slug = 'missing',
    f => f.topics[0].evidence_ids = ['unrelated'],
    f => f.topics[0].article_slug = 'different',
  ]) {
    const f = fixture(); alter(f); assert.throws(() => validateRelease(f));
  }
});
test('sitemap includes published pages only and never indexes preview builds', () => {
  const articles = [{ id: 'published', data: { draft: false } }, { id: 'hidden', data: { draft: true } }];
  const xml = sitemapXML(articles);
  assert.ok(xml.includes(`${siteOrigin}/articles/published/`));
  assert.ok(xml.includes(`${siteOrigin}/methodology/`));
  assert.ok(!xml.includes('hidden'));
  assert.ok(!sitemapXML(articles, true).includes('<url>'));
  assert.match(robotsText(true), /Disallow: \/\n/);
  assert.ok(!robotsText(true).includes('Sitemap:'));
  assert.ok(robotsText().includes(`Sitemap: ${siteOrigin}/sitemap.xml`));
});
test('sitemap validates slugs before constructing canonical routes', () => {
  assert.throws(() => sitemapXML([{ id: '../escape', data: { draft: false } }]));
});
