import { getCollection, type CollectionEntry } from 'astro:content';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { publicationContext } from './data';
import { selectArticles, validateArticles } from './publication.mjs';
export const showDrafts = process.env.SHOW_DRAFTS === 'true';
export async function getArticles(): Promise<CollectionEntry<'articles'>[]> {
  const articles = await getCollection('articles');
  for (const article of articles) {
    const raw = readFileSync(join(process.cwd(), 'content/articles', `${article.id}.md`), 'utf8');
    const match = /^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)([\s\S]*)$/.exec(raw);
    if (!match) throw new Error(`Invalid frontmatter delimiter: ${article.id}`);
    article.body = match[1];
  }
  validateArticles(articles, publicationContext);
  const visible: CollectionEntry<'articles'>[] = selectArticles(articles, showDrafts);
  return visible.sort((a, b) =>
    b.data.date.valueOf() - a.data.date.valueOf() || a.id.localeCompare(b.id));
}
