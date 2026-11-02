import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { inspectBuiltSite } from './site-output.mjs';

const distDir = resolve(process.argv[2] ?? 'dist');
if (!existsSync(distDir)) throw new Error(`Build directory does not exist: ${distDir}`);
const articles = readdirSync('content/articles').filter((file) => file.endsWith('.md')).map((file) => {
  const raw = readFileSync(join('content/articles', file), 'utf8');
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---/.exec(raw)?.[1] ?? '';
  return { id: file.replace(/\.md$/, ''), draft: !/^draft:\s*false\s*$/m.test(frontmatter) };
});
const result = inspectBuiltSite({ distDir, articles, showDrafts: process.env.SHOW_DRAFTS === 'true' });
if (result.errors.length) {
  console.error(result.errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log(`Static site checks passed: ${result.htmlPages} Arabic RTL pages, ${result.localLinks} local links, ${result.scriptBytes} browser JavaScript bytes, largest HTML ${result.largestHtmlBytes} bytes.`);
  console.log(`Draft routes: ${process.env.SHOW_DRAFTS === 'true' ? 'present only with visible notices and noindex' : 'excluded from production'}.`);
}
