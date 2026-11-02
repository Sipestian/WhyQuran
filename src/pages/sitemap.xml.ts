import { getArticles, showDrafts } from '../lib/articles';
import { sitemapXML } from '../lib/site.mjs';
export async function GET() {
  return new Response(sitemapXML(await getArticles(), showDrafts), {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
}
