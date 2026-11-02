import { createHash } from 'node:crypto';

/** Validate editorial release metadata before any routes are generated. */
export function validateArticles(articles, { evidenceIds, reviewFiles, readerIds, reviewRecords }) {
  for (const { id, data, body } of articles) {
    const fail = (message) => { throw new Error(`[${id}] ${message}`); };
    if (!Array.isArray(data.evidence_ids) || data.evidence_ids.length === 0) {
      fail('evidence_ids must contain at least one existing record');
    }
    for (const evidence of data.evidence_ids) {
      if (!evidenceIds.has(evidence)) fail(`Unknown evidence_ids reference: ${evidence}`);
    }
    if (data.draft !== false) continue;
    if (!Array.isArray(data.reviewed_by) || data.reviewed_by.length === 0 ||
        data.reviewed_by.some((reviewer) => typeof reviewer !== 'string' || !reviewer.trim())) {
      fail('reviewed_by must identify the independent reviewer');
    }
    if (data.reviewed_by.some((reviewer) => !readerIds.has(reviewer))) {
      fail('reviewed_by must have a complete reading ledger');
    }
    const date = data.reviewed_at;
    if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
        !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) {
      fail('reviewed_at must be a valid YYYY-MM-DD date');
    }
    if (typeof data.review_record !== 'string' ||
        !/^research\/reviews\/[a-zA-Z0-9_-]+\.json$/.test(data.review_record) ||
        !reviewFiles.has(data.review_record)) {
      fail('review_record must reference an existing file inside research/reviews/');
    }
    const review = reviewRecords.get(data.review_record);
    const entry = review?.articles?.[id];
    if (!entry) fail('review_record has no review entry for this article');
    if (review.review_type !== 'internal_ai' || review.date !== date || entry.verdict !== 'approved' ||
        !Array.isArray(entry.reviewers) ||
        JSON.stringify([...entry.reviewers].sort()) !== JSON.stringify([...data.reviewed_by].sort())) {
      fail('review_record approval, reviewers or date do not match the article');
    }
    if (typeof body !== 'string' || createHash('sha256').update(body.trim(), 'utf8').digest('hex') !== entry.body_sha256) {
      fail('review_record body_sha256 does not match the reviewed Markdown body');
    }
  }
}

export function selectArticles(articles, showDrafts = false) {
  return articles.filter(({ data }) => data.draft === false || showDrafts === true);
}
