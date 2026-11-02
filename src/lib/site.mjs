export const siteOrigin = 'https://whyqaraan.cometgleam256.chatgpt.site';
const pages = ['/', '/articles/', '/counts/', '/research/', '/methodology/'];

export function sitemapXML(articles, preview = false) {
  const paths = preview ? [] : [...pages, ...articles.filter(article => article.data.draft === false).map(article => {
    if (!/^[a-z0-9-]+$/.test(article.id)) throw new Error(`Invalid article slug: ${article.id}`);
    return `/articles/${article.id}/`;
  })];
  return '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    [...new Set(paths)].map(path => `  <url><loc>${new URL(path, siteOrigin).href}</loc></url>`).join('\n') +
    '\n</urlset>\n';
}

export function robotsText(preview = false) {
  return preview ? 'User-agent: *\nDisallow: /\n' : `User-agent: *\nAllow: /\nSitemap: ${siteOrigin}/sitemap.xml\n`;
}
