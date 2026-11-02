import { showDrafts } from '../lib/articles';
import { robotsText } from '../lib/site.mjs';
export function GET() {
  return new Response(robotsText(showDrafts), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
