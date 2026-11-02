import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const articles = defineCollection({
  loader: glob({ pattern: '*.md', base: './content/articles' }),
  schema: z.object({
    title: z.string().min(1),
    description: z.string().min(1),
    date: z.coerce.date(),
    draft: z.boolean().default(true),
    category: z.enum(['wording', 'counts', 'science', 'family', 'family_law', 'methodology']),
    evidence_ids: z.array(z.string()).min(1),
    reviewed_by: z.array(z.string()).optional(),
    reviewed_at: z.preprocess((v) => v instanceof Date ? v.toISOString().slice(0, 10) : v, z.string().optional()),
    review_record: z.string().optional(),
  }),
});
export const collections = { articles };
