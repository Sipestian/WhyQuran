import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

function filesIn(root, directory = root) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesIn(root, path) : [relative(root, path).replaceAll('\\', '/')];
  });
}
const attrs = (tag) => Object.fromEntries([...tag.matchAll(/([\w-]+)\s*=\s*["']([^"']*)["']/g)].map((match) => [match[1].toLowerCase(), match[2]]));
const decode = (value) => value.replaceAll('&amp;', '&').replaceAll('&#x26;', '&').replaceAll('&#38;', '&');

export function inspectBuiltSite({ distDir, articles, showDrafts }) {
  const errors = [];
  const files = filesIn(distDir);
  const fileSet = new Set(files);
  const html = new Map(files.filter((file) => file.endsWith('.html')).map((file) => [file, readFileSync(join(distDir, file), 'utf8')]));
  const scriptBytes = files.filter((file) => /\.(?:m?js)$/.test(file)).reduce((total, file) => total + statSync(join(distDir, file)).size, 0);
  if (scriptBytes > 0) errors.push(`Browser JavaScript budget exceeded: ${scriptBytes} bytes (budget: 0)`);
  if (files.some((file) => file.endsWith('word-index.json'))) errors.push('The full word index must not be shipped with the reading site');
  let localLinks = 0;
  for (const [file, content] of html) {
    const rootAttrs = attrs(content.match(/<html\b[^>]*>/i)?.[0] ?? '');
    if (rootAttrs.lang !== 'ar' || rootAttrs.dir !== 'rtl') errors.push(`${file}: expected lang="ar" and dir="rtl"`);
    if (Buffer.byteLength(content) > 350_000) errors.push(`${file}: HTML exceeds the 350 kB page budget`);
    for (const script of content.matchAll(/<script\b[^>]*>/gi)) {
      if (!['application/ld+json', 'application/json'].includes(attrs(script[0]).type)) errors.push(`${file}: executable JavaScript in a reading page`);
    }
    const route = `/${file.replace(/index\.html$/, '')}`;
    for (const attribute of content.matchAll(/\b(?:href|src|poster)\s*=\s*["']([^"']+)["']/gi)) {
      const value = decode(attribute[1]);
      if (/^javascript:/i.test(value)) { errors.push(`${file}: JavaScript URL`); continue; }
      let url;
      try { url = new URL(value, `https://local.test${route}`); } catch { errors.push(`${file}: invalid URL ${value}`); continue; }
      if (url.origin !== 'https://local.test') continue;
      localLinks++;
      let pathname;
      try { pathname = decodeURIComponent(url.pathname).replace(/^\//, ''); } catch { errors.push(`${file}: invalid escaped URL ${value}`); continue; }
      const candidate = !pathname || pathname.endsWith('/') ? `${pathname}index.html` : pathname;
      const target = fileSet.has(candidate) ? candidate : fileSet.has(`${candidate}/index.html`) ? `${candidate}/index.html` : null;
      if (!target) { errors.push(`${file}: broken local link ${value}`); continue; }
      if (url.hash && html.has(target)) {
        let anchor;
        try { anchor = decodeURIComponent(url.hash.slice(1)); } catch { errors.push(`${file}: invalid anchor ${value}`); continue; }
        const ids = new Set([...html.get(target).matchAll(/\bid\s*=\s*["']([^"']+)["']/g)].map((match) => decode(match[1])));
        if (!ids.has(anchor)) errors.push(`${file}: missing anchor ${value}`);
      }
    }
  }
  for (const article of articles) {
    const route = `articles/${article.id}/index.html`;
    const exists = fileSet.has(route) || fileSet.has(`articles/${article.id}.html`);
    if (article.draft && !showDrafts) {
      if (exists) errors.push(`Draft route leaked into production: /articles/${article.id}/`);
      continue;
    }
    if (!exists) { errors.push(`Expected article route missing: /articles/${article.id}/`); continue; }
    if (article.draft) {
      const content = html.get(route) ?? html.get(`articles/${article.id}.html`) ?? '';
      const robots = [...content.matchAll(/<meta\b[^>]*>/gi)].map((match) => attrs(match[0])).find((meta) => meta.name === 'robots');
      if (!robots?.content?.split(/\s*,\s*/).includes('noindex')) errors.push(`${route}: preview draft needs noindex`);
      if (!/\bdata-draft-notice(?:\s|=|>)/.test(content)) errors.push(`${route}: preview needs a visible draft notice`);
    }
  }
  return { errors, htmlPages: html.size, localLinks, scriptBytes, largestHtmlBytes: Math.max(0, ...[...html.values()].map((body) => Buffer.byteLength(body))) };
}
