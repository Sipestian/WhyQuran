import test from 'node:test';
import assert from 'node:assert/strict';
import { validateBacklog } from '../src/lib/backlog.mjs';
const context = { evidenceIds: new Set(['known-record']), verseRefs: new Set(['1:1', '1:7']) };
const topic = () => ({
  id: 'open-question', title_ar: 'سؤال مفتوح', category: 'wording', status: 'idea',
  question_ar: 'ما السؤال؟', baseline_ar: 'ما نعرفه', verse_refs: ['1:7'],
  evidence_ids: ['known-record'], source_urls: ['https://example.org/source'],
  article_slug: null, next_step_ar: 'مراجعة السياق', qualification_ar: 'لم يحسم بعد',
});

test('a future article slug is valid without a published article', () => {
  const entry = topic(); entry.article_slug = 'future-article';
  assert.doesNotThrow(() => validateBacklog([entry], context));
});

test('duplicate topic IDs fail instead of merging distinct topics', () => {
  assert.throws(() => validateBacklog([topic(), topic()], context), /duplicate/i);
});

test('unknown statuses and categories fail instead of losing their labels', () => {
  for (const field of ['category', 'status']) {
    const entry = topic(); entry[field] = 'unrecognized';
    assert.throws(() => validateBacklog([entry], context), new RegExp(field));
  }
});

test('topic references must resolve to existing evidence and verse ranges', () => {
  const entry = topic(); entry.evidence_ids = ['missing'];
  assert.throws(() => validateBacklog([entry], context), /missing/);
  entry.evidence_ids = []; entry.verse_refs = ['1:8'];
  assert.throws(() => validateBacklog([entry], context), /1:8/);
});

test('source URLs must be absolute HTTP or HTTPS links', () => {
  for (const url of ['javascript:alert(1)', '/local/file', 'https://']) {
    const entry = topic(); entry.source_urls = [url];
    assert.throws(() => validateBacklog([entry], context), /source_urls/);
  }
});

test('article slugs cannot escape their route', () => {
  const entry = topic(); entry.article_slug = '../private';
  assert.throws(() => validateBacklog([entry], context), /article_slug/);
});
