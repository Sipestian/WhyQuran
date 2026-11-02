import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
const downloads: Record<string, string> = {
  ...Object.fromEntries(['repetition-summary', 'characters-simple-clean', 'characters-uthmani', 'universe', 'audit']
    .map((name) => [name, `reports/${name}.json`])),
  'day-month': 'research/annotations/day-month.json',
  'wife-wording': 'research/annotations/wife-wording.json',
  'light-wording': 'research/annotations/light-wording.json',
};
export function getStaticPaths() {
  return Object.keys(downloads).map((name) => ({ params: { name } }));
}
export const GET: APIRoute = ({ params }) => new Response(
  readFileSync(join(process.cwd(), downloads[params.name!]), 'utf8'),
  { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
);
