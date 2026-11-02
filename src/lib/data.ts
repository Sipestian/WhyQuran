import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { validateBacklog } from './backlog.mjs';
import { validateResearch } from '../../scripts/research-validation.mjs';

export const projectRoot = process.cwd();
const verifiedResearch = validateResearch(projectRoot);
export function readJSON<T = any>(path: string): T {
  return JSON.parse(readFileSync(join(projectRoot, path), 'utf8'));
}
export interface Evidence {
  id: string; title_ar: string; category: string; status: string;
  claim_ar: string; limitations_ar: string[];
  sources: { id: string; title: string; url: string; kind: string; supports_ar: string }[];
  [key: string]: unknown;
}
export interface Topic {
  id: string; title_ar: string; category: string; status: string;
  question_ar: string; baseline_ar: string; verse_refs: string[]; evidence_ids: string[];
  source_urls: string[]; article_slug: string | null; next_step_ar: string; qualification_ar: string;
}
export const evidence: Evidence[] = readdirSync(join(projectRoot, 'research/records'))
  .filter((file) => file.endsWith('.json')).sort().map((file) => readJSON(`research/records/${file}`));
export const evidenceById = new Map(evidence.map((record) => [record.id, record]));
if (evidenceById.size !== evidence.length) throw new Error('Duplicate evidence IDs');
for (const record of evidence) {
  if (!/^[a-z0-9-]+$/.test(record.id)) throw new Error(`Invalid evidence ID: ${record.id}`);
}
const reviewsPath = join(projectRoot, 'research/reviews');
const reviewFiles = new Set(existsSync(reviewsPath) ? readdirSync(reviewsPath).map((file) => `research/reviews/${file}`) : []);
export const publicationContext = {
  evidenceIds: new Set(evidenceById.keys()), reviewFiles,
  reviewRecords: new Map([...reviewFiles].filter((path) => path.endsWith('.json')).map((path) => [path, readJSON(path)])),
  readerIds: new Set<string>(verifiedResearch.reader_ids),
};
export const backlog = readJSON<Topic[]>('research/website-backlog.json');
const verseRefs = new Set(readFileSync(join(projectRoot, 'data/source/tanzil-simple-clean.txt'), 'utf8')
  .split('\n').flatMap((line) => {
    const match = /^(\d+)\|(\d+)\|/.exec(line);
    return match ? [`${match[1]}:${match[2]}`] : [];
  }));
validateBacklog(backlog, { evidenceIds: publicationContext.evidenceIds, verseRefs });
export const manifest = readJSON('data/manifest.json');
export const number = (value: number) => new Intl.NumberFormat('ar-SA').format(value);
export const dateLabel = (date: Date | string) => new Intl.DateTimeFormat('ar-SA', {
  calendar: 'gregory', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
}).format(new Date(date));
