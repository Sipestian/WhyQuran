export const categories = {
  wording: 'الألفاظ والسياق', counts: 'الأعداد والتكرار', science: 'القرآن والعلم',
  family: 'الأسرة والأحكام', methodology: 'منهج البحث',
};
export const statuses = {
  idea: 'سؤال مفتوح', research: 'قيد البحث', draft: 'مسودة مقال', reviewed: 'مراجعة داخلية مكتملة',
};
export const categoryKey = (category) => category === 'family_law' ? 'family' : category;
export const categoryLabel = (category) => categories[categoryKey(category)] ?? category;

export function validateBacklog(topics, { evidenceIds, verseRefs }) {
  if (!Array.isArray(topics)) throw new Error('The research backlog must be an array');
  const ids = new Set();
  for (const topic of topics) {
    const fail = (message) => { throw new Error(`[backlog: ${topic.id}] ${message}`); };
    if (typeof topic.id !== 'string' || !/^[a-z0-9-]+$/.test(topic.id)) fail('Invalid id');
    if (ids.has(topic.id)) fail('Duplicate topic id');
    ids.add(topic.id);
    if (!Object.hasOwn(categories, topic.category)) fail('Unknown category');
    if (!Object.hasOwn(statuses, topic.status)) fail('Unknown status');
    for (const field of ['title_ar', 'question_ar', 'baseline_ar', 'next_step_ar', 'qualification_ar']) {
      if (typeof topic[field] !== 'string' || !topic[field].trim()) fail(`Missing ${field}`);
    }
    for (const field of ['evidence_ids', 'verse_refs', 'source_urls']) {
      if (!Array.isArray(topic[field])) fail(`${field} must be an array`);
    }
    for (const id of topic.evidence_ids) if (!evidenceIds.has(id)) fail(`Unknown evidence_ids reference: ${id}`);
    for (const ref of topic.verse_refs) if (!verseRefs.has(ref)) fail(`Unknown verse_refs reference: ${ref}`);
    for (const url of topic.source_urls) {
      try {
        const parsed = new URL(url);
        if (!['https:', 'http:'].includes(parsed.protocol) || !parsed.hostname) fail('Invalid source_urls');
      } catch { fail('Invalid source_urls'); }
    }
    if (topic.article_slug !== null && (typeof topic.article_slug !== 'string' || !/^[a-z0-9-]+$/.test(topic.article_slug))) {
      fail('Invalid article_slug');
    }
  }
}
