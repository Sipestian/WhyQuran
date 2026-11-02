import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceStatusLabel } from '../src/lib/evidence-status.mjs';

test('canonical evidence statuses retain their actual level of certainty', () => {
  const expected = {
    documented_interpretation: 'تفسير موثق',
    scientific_comparison: 'مقارنة علمية محدودة',
    reproduced_observation: 'ملاحظة أعيد التحقق منها',
    hypothesis: 'فرضية تحتاج إلى اختبار',
    needs_verification: 'تحتاج إلى تحقق',
  };
  for (const [status, label] of Object.entries(expected)) assert.equal(evidenceStatusLabel(status), label);
});

test('an unknown evidence status never becomes a documented finding', () => {
  assert.throws(() => evidenceStatusLabel('future-unknown-status'), /Unknown evidence status/);
});
