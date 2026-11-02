import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { inspectBuiltSite } from '../scripts/site-output.mjs';

function fixture(t, files) {
  const root = mkdtempSync(join(tmpdir(), 'whyqaraan-site-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const [name, body] of Object.entries(files)) {
    mkdirSync(dirname(join(root, name)), { recursive: true });
    writeFileSync(join(root, name), body);
  }
  return root;
}
const html = (body, head = '') => `<!doctype html><html lang="ar" dir="rtl"><head>${head}</head><body><main id="main">${body}</main></body></html>`;

test('built local links and target anchors must exist', (t) => {
  const distDir = fixture(t, { 'index.html': html('<a href="/missing/">رابط</a><a href="#absent">قسم</a>') });
  const result = inspectBuiltSite({ distDir, articles: [], showDrafts: false });
  assert.ok(result.errors.some((error) => error.includes('/missing/')));
  assert.ok(result.errors.some((error) => error.includes('#absent')));
});

test('production rejects a draft direct route even with no link to it', (t) => {
  const distDir = fixture(t, { 'index.html': html('الرئيسية'), 'articles/secret/index.html': html('مسودة') });
  const result = inspectBuiltSite({ distDir, articles: [{ id: 'secret', draft: true }], showDrafts: false });
  assert.ok(result.errors.some((error) => error.includes('Draft route')));
});

test('preview draft routes require noindex and a visible draft notice', (t) => {
  const distDir = fixture(t, { 'articles/secret/index.html': html('مسودة بلا تنبيه') });
  const result = inspectBuiltSite({ distDir, articles: [{ id: 'secret', draft: true }], showDrafts: true });
  assert.ok(result.errors.some((error) => error.includes('noindex')));
  assert.ok(result.errors.some((error) => error.includes('draft notice')));
});

test('an LTR page or browser JavaScript breaks the reading budget', (t) => {
  const distDir = fixture(t, { 'index.html': '<html lang="en" dir="ltr"><script>console.log(1)</script></html>', 'app.js': 'alert(1)' });
  const result = inspectBuiltSite({ distDir, articles: [], showDrafts: false });
  assert.ok(result.errors.some((error) => error.includes('lang="ar"')));
  assert.ok(result.errors.some((error) => error.includes('JavaScript')));
});

test('valid RTL files, anchors, downloads and marked preview drafts pass', (t) => {
  const distDir = fixture(t, {
    'index.html': html('<a href="/">الرئيسية</a><a href="#main">المحتوى</a><a href="/articles/secret/#main">اقرأ</a><a href="/evidence/one.json">دليل</a>'),
    'articles/secret/index.html': html('<aside data-draft-notice>مسودة للمراجعة</aside>', '<meta name="robots" content="noindex, nofollow">'),
    'evidence/one.json': '{}',
  });
  assert.deepEqual(inspectBuiltSite({ distDir, articles: [{ id: 'secret', draft: true }], showDrafts: true }).errors, []);
});
