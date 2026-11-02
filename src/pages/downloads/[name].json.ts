import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
export function getStaticPaths() {
  return ['repetition-summary', 'characters-simple-clean', 'characters-uthmani', 'universe', 'audit']
    .map((name) => ({ params: { name } }));
}
export const GET: APIRoute = ({ params }) => new Response(
  readFileSync(join(process.cwd(), 'reports', `${params.name}.json`), 'utf8'),
  { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
);
