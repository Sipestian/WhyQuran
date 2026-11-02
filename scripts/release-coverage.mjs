/** Editorial coverage is verified separately from the truth of any proposed claim. */
export function validateRelease({ topics, entries, articles }) {
  const fail = message => { throw new Error(`Release coverage: ${message}`); };
  const topicMap = new Map(topics.map(topic => [topic.id, topic]));
  const articleMap = new Map(articles.map(article => [article.id, article]));
  const seen = new Set();
  for (const entry of entries) {
    if (seen.has(entry.topic_id)) fail(`duplicate topic ${entry.topic_id}`);
    seen.add(entry.topic_id);
    const topic = topicMap.get(entry.topic_id);
    if (!topic) fail(`unknown topic ${entry.topic_id}`);
    if (topic.status !== 'reviewed') fail(`topic is not reviewed: ${topic.id}`);
    if (topic.article_slug !== entry.article_slug) fail(`article mapping differs: ${topic.id}`);
    const article = articleMap.get(entry.article_slug);
    if (!article || article.draft !== false) fail(`published article missing: ${entry.article_slug}`);
    if (!topic.evidence_ids?.length || !topic.evidence_ids.some(id => article.evidence_ids.includes(id))) {
      fail(`topic and article have no shared evidence: ${topic.id}`);
    }
  }
  for (const id of topicMap.keys()) if (!seen.has(id)) fail(`uncovered topic ${id}`);
  return { topics: seen.size, articles: new Set(entries.map(entry => entry.article_slug)).size };
}
