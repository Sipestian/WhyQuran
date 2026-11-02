import type { APIRoute } from 'astro';
import { readFileSync } from 'node:fs';
export const GET: APIRoute = () => new Response(readFileSync('data/SOURCE-LICENSE.txt', 'utf8'), {
  headers: { 'Content-Type': 'text/plain; charset=utf-8' },
});
