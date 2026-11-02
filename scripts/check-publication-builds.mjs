import assert from 'node:assert/strict';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { basename, join, relative } from 'node:path';
import { execFileSync } from 'node:child_process';
import { inspectBuiltSite } from './site-output.mjs';
import { validateResearch } from './research-validation.mjs';

// Build a disposable copy so the editorial tree is never changed by this check.
const source = process.cwd();
function dependencyCacheSnapshot() {
  const result = {};
  function visit(directory) {
    if (!existsSync(directory)) return;
    for (const item of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, item.name);
      if (item.isDirectory()) visit(path);
      else if (item.isFile()) result[relative(source, path)] = createHash('sha256').update(readFileSync(path)).digest('hex');
    }
  }
  for (const name of ['.astro', '.vite']) visit(join(source, 'node_modules', name));
  return result;
}
const dependencyCachesBefore = dependencyCacheSnapshot();
const work = mkdtempSync(join(tmpdir(), 'whyqaraan-publication-'));
try {
  for (const path of ['src', 'public', 'content', 'scripts', 'quran_research', 'research', 'Makefile', 'package.json', 'astro.config.mjs', 'tsconfig.json']) {
    cpSync(join(source, path), join(work, path), { recursive: true });
  }
  for (const path of ['node_modules', 'data']) symlinkSync(join(source, path), join(work, path), 'dir');
  mkdirSync(join(work, 'reports'));
  cpSync(join(source, 'reports/audit.json'), join(work, 'reports/audit.json'));
  const staleReport = join(work, 'reports/repetition-summary.json');
  writeFileSync(staleReport, JSON.stringify({ tokens: -1 }));
  mkdirSync(join(work, 'content/articles'), { recursive: true });
  const firstRecord = readdirSync(join(source, 'research/records')).find((file) => file.endsWith('.json'));
  const evidenceId = JSON.parse(readFileSync(join(source, 'research/records', firstRecord), 'utf8')).id;
  const slug = 'site-integration-draft';
  writeFileSync(join(work, 'content/articles', `${slug}.md`), `---\ntitle: 'مسودة اختبار معزولة'\ndescription: 'هذه مادة اصطناعية للتحقق من بوابة النشر: ${basename(work)}.'\ndate: 2026-11-02\ndraft: true\ncategory: methodology\nevidence_ids: [${evidenceId}]\n---\n\nمادة اختبار لا تكتب في شجرة المقالات الأصلية.\n`);
  for (const showDrafts of [false, true]) {
    const output = showDrafts ? 'dist-preview' : 'dist';
    execFileSync(process.execPath, [join(work, 'node_modules/astro/bin/astro.mjs'), 'build', '--outDir', output], {
      cwd: work,
      env: { ...process.env, SHOW_DRAFTS: showDrafts ? 'true' : '', ASTRO_TELEMETRY_DISABLED: '1' },
      stdio: ['ignore', 'pipe', 'pipe'], timeout: 120_000,
    });
    const result = inspectBuiltSite({ distDir: join(work, output), articles: [{ id: slug, draft: true }], showDrafts });
    assert.deepEqual(result.errors, [], result.errors.join('\n'));
    const sitemap = readFileSync(join(work, output, 'sitemap.xml'), 'utf8');
    const robots = readFileSync(join(work, output, 'robots.txt'), 'utf8');
    assert.equal(sitemap.includes(`/articles/${slug}/`), false, 'Synthetic drafts must never enter a sitemap');
    if (showDrafts) {
      assert.equal(sitemap.includes('<url>'), false, 'Preview builds must emit an empty sitemap');
      assert.match(robots, /Disallow: \/\n/, 'Preview robots must block crawling');
    } else {
      assert.match(sitemap, /<loc>https:\/\/whyqaraan\.cometgleam256\.chatgpt\.site\/articles\/word-counts\/<\/loc>/);
      assert.match(robots, /Sitemap: https:\/\/whyqaraan\.cometgleam256\.chatgpt\.site\/sitemap.xml/);
    }
    assert.equal(JSON.parse(readFileSync(join(work, output, 'downloads/repetition-summary.json'), 'utf8')).tokens, 77800, 'Direct Astro builds must replace stale reports with freshly verified counts');
    assert.deepEqual(dependencyCacheSnapshot(), dependencyCachesBefore, 'Integration builds must not mutate shared dependency caches');
    console.log(`Real Astro ${showDrafts ? 'preview' : 'production'} build passed: ${result.htmlPages} pages; synthetic draft ${showDrafts ? 'visible with noindex and notice' : 'has no direct route'}.`);
  }
  const annotationName = readdirSync(join(work, 'research/annotations')).filter((file) => file.endsWith('.json')).sort()[0];
  const annotationPath = join(work, 'research/annotations', annotationName);
  const annotationText = readFileSync(annotationPath, 'utf8');
  const invalidAnnotation = JSON.parse(annotationText);
  assert.ok(invalidAnnotation.occurrences.length > 0, 'The annotation rejection check needs a real occurrence');
  invalidAnnotation.occurrences.pop();
  writeFileSync(annotationPath, JSON.stringify(invalidAnnotation));
  assert.throws(() => validateResearch(work), (error) => error.message.includes(annotationName) && error.message.includes('ناقص 1'),
    'The canonical validator must identify the file and exactly one missing occurrence');
  assert.throws(() => execFileSync(process.execPath, [join(work, 'node_modules/astro/bin/astro.mjs'), 'build'], {
    cwd: work, env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1' },
    stdio: ['ignore', 'pipe', 'pipe'], timeout: 120_000,
  }), (error) => error.status === 1,
  'Direct Astro builds must reject a missing corpus occurrence');
  writeFileSync(annotationPath, annotationText);
  console.log('Direct Astro build rejected a missing annotation occurrence.');
  const ledgerPath = join(work, 'research/readings/arabic_wording.json');
  const invalidLedger = JSON.parse(readFileSync(ledgerPath, 'utf8'));
  invalidLedger.blocks = [];
  writeFileSync(ledgerPath, JSON.stringify(invalidLedger));
  assert.throws(() => validateResearch(work), /Research validation failed/);
  assert.throws(() => execFileSync(process.execPath, [join(work, 'node_modules/astro/bin/astro.mjs'), 'build'], {
    cwd: work, env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1' },
    stdio: ['ignore', 'pipe', 'pipe'], timeout: 120_000,
  }), (error) => error.status === 1, 'Direct Astro builds must reject completed:true with empty blocks');
  console.log('Direct Astro build rejected the invalid completed:true reading ledger.');
  assert.deepEqual(dependencyCacheSnapshot(), dependencyCachesBefore, 'Rejected builds must not mutate shared dependency caches');
  const sourceStore = join(source, '.astro/cache/data-store.json');
  if (existsSync(sourceStore)) assert.equal(readFileSync(sourceStore, 'utf8').includes(slug), false, 'The synthetic draft must not leak into the original project collection');
  console.log('Shared node_modules/.astro and node_modules/.vite caches remained unchanged.');
} finally {
  rmSync(work, { recursive: true, force: true });
}
