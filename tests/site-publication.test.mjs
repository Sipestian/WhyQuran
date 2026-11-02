import test from 'node:test';
import assert from 'node:assert/strict';
import { validateArticles, selectArticles } from '../src/lib/publication.mjs';

const context = {
  evidenceIds: new Set(['evidence-one']),
  reviewFiles: new Set(['research/reviews/article-one.json']),
  readerIds: new Set(['independent-reader']),
  reviewRecords: new Map([['research/reviews/article-one.json', {
    date: '2026-11-02', review_type: 'internal_ai', articles: {
      'article-one': { verdict: 'approved', reviewers: ['independent-reader'], body_sha256: 'b4052a9246c9e48778f3d6423c4f47a33c0cecc714c9036359429c87ba190591' },
    },
  }]]),
};
const published = () => ({
  id: 'article-one',
  body: 'مقال اختباري.',
  data: {
    title: 'مقال مراجع', draft: false, evidence_ids: ['evidence-one'],
    reviewed_by: ['independent-reader'], reviewed_at: '2026-11-02',
    review_record: 'research/reviews/article-one.json',
  },
});

test('production excludes a draft even when it has review metadata', () => {
  const draft = published(); draft.id = 'unpublished'; draft.data.draft = true;
  assert.deepEqual(selectArticles([published(), draft], false).map((a) => a.id), ['article-one']);
  assert.deepEqual(selectArticles([published(), draft], true).map((a) => a.id), ['article-one', 'unpublished']);
});

test('missing draft flag does not publish an article', () => {
  const article = published(); delete article.data.draft;
  assert.deepEqual(selectArticles([article], false), []);
});

test('a reviewed article with existing evidence and review record passes', () => {
  assert.doesNotThrow(() => validateArticles([published()], context));
});

test('publication fails without an independent reviewer identity', () => {
  const article = published(); article.data.reviewed_by = [];
  assert.throws(() => validateArticles([article], context), /reviewed_by/);
});

test('publication rejects a reviewer without a complete reading ledger', () => {
  const article = published(); article.data.reviewed_by = ['unknown-reader'];
  assert.throws(() => validateArticles([article], context), /reading ledger/);
});

test('publication rejects a missing or impossible review date', () => {
  for (const date of [undefined, '2026-02-30', 'November 2, 2026']) {
    const article = published(); article.data.reviewed_at = date;
    assert.throws(() => validateArticles([article], context), /reviewed_at/);
  }
});

test('publication fails when its review record is absent or outside the review directory', () => {
  for (const path of [undefined, 'research/reviews/missing.json', 'research/reviews/../../README.md']) {
    const article = published(); article.data.review_record = path;
    assert.throws(() => validateArticles([article], context), /review_record/);
  }
});

test('missing evidence fails for published articles and preview drafts', () => {
  for (const draft of [false, true]) {
    const article = published(); article.data.draft = draft;
    article.data.evidence_ids = ['unknown-evidence'];
    assert.throws(() => validateArticles([article], context), /unknown-evidence/);
  }
});

test('an article cannot be published with no evidence', () => {
  const article = published(); article.data.evidence_ids = [];
  assert.throws(() => validateArticles([article], context), /evidence_ids/);
});

test('preview drafts do not need publication metadata', () => {
  const article = { id: 'draft', data: { draft: true, evidence_ids: ['evidence-one'] } };
  assert.doesNotThrow(() => validateArticles([article], context));
});

test('editing reviewed article text invalidates publication until re-reviewed', () => {
  const article = published(); article.body = 'متن مختلف بعد المراجعة.';
  assert.throws(() => validateArticles([article], context), /body_sha256/);
});

test('a review for another article cannot approve this article', () => {
  const article = published(); article.id = 'other-article';
  assert.throws(() => validateArticles([article], context), /review entry/);
});

test('rejected reviews and mismatched date or reviewers cannot publish', () => {
  for (const field of ['verdict', 'reviewers', 'date']) {
    const review = structuredClone(context.reviewRecords.get('research/reviews/article-one.json'));
    if (field === 'date') review.date = '2026-11-01';
    else review.articles['article-one'][field] = field === 'verdict' ? 'changes_requested' : ['another-reader'];
    const changedContext = { ...context, reviewRecords: new Map([['research/reviews/article-one.json', review]]) };
    assert.throws(() => validateArticles([published()], changedContext), /review_record/);
  }
});
