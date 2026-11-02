import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { evidence, projectRoot } from '../../lib/data';
export function getStaticPaths() {
  return evidence.map((record) => ({ params: { id: record.id } }));
}
export const GET: APIRoute = ({ params }) => new Response(
  readFileSync(join(projectRoot, 'research/records', `${params.id}.json`), 'utf8'),
  { headers: { 'Content-Type': 'application/json; charset=utf-8' } },
);
