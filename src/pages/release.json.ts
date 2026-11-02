import { backlog, readJSON } from '../lib/data';
import { getArticles } from '../lib/articles';
export async function GET() {
  const articles = await getArticles();
  return new Response(JSON.stringify({
    scope_ar: 'تغطية تحريرية للموضوعات المسجلة؛ لا تعني إثبات كل دعوى أو انتهاء البحث.',
    topics: backlog.map(({ id, status, article_slug, evidence_ids }) => ({ id, status, article_slug, evidence_ids })),
    entries: readJSON('research/release-plan.json').entries.map(({ topic_id, article_slug }: { topic_id: string; article_slug: string }) => ({ topic_id, article_slug })),
    articles: articles.map(({ id, data }) => ({ id, draft: data.draft, evidence_ids: data.evidence_ids })),
  }, null, 2), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
