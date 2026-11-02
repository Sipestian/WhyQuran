import test from 'node:test';
import assert from 'node:assert/strict';
import { cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { validateResearch } from '../scripts/research-validation.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'whyqaraan-research-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const name of ['research', 'quran_research']) cpSync(join(process.cwd(), name), join(root, name), { recursive: true });
  symlinkSync(join(process.cwd(), 'data'), join(root, 'data'), 'dir');
  const path = join(root, 'research/readings/arabic_wording.json');
  const ledger = JSON.parse(readFileSync(path, 'utf8'));
  return { root, path, ledger };
}

test('canonical research validation returns only verified readers without writing reports', (t) => {
  const { root } = fixture(t);
  assert.ok(validateResearch(root).reader_ids.includes('arabic_wording'));
  assert.equal(existsSync(join(root, 'reports')), false);
});

for (const [name, mutate] of [
  ['empty blocks', (ledger) => { ledger.blocks = []; }],
  ['a gap in coverage', (ledger) => { ledger.blocks.shift(); }],
  ['a wrong corpus hash', (ledger) => { ledger.corpus_sha256 = '0'.repeat(64); }],
  ['a program-only reading method', (ledger) => { ledger.method = 'programmatic_count'; }],
]) {
  test(`completed:true cannot authorize ${name}`, (t) => {
    const { root, path, ledger } = fixture(t);
    assert.equal(ledger.completed, true);
    mutate(ledger);
    writeFileSync(path, JSON.stringify(ledger));
    assert.throws(() => validateResearch(root), /Research validation failed/);
  });
}

test('missing canonical Python module fails closed', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'whyqaraan-missing-validator-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, 'research/readings'), { recursive: true });
  assert.throws(() => validateResearch(root), /Research validation failed/);
});
