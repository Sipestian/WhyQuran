import { execFileSync } from 'node:child_process';

const validation = `
import json
import sys
from pathlib import Path
from quran_research.catalog import build_catalog

catalog = build_catalog(Path(sys.argv[1]))
print(json.dumps({'reader_ids': [reader['reader_id'] for reader in catalog['readers']]}))
`;

// The canonical Python function verifies sources, every reading block, and records.
// It returns data without writing a report. Never fall back to completed:true.
export function validateResearch(root) {
  try {
    return JSON.parse(execFileSync('python3', ['-c', validation, root], {
      cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 60_000,
    }));
  } catch (error) {
    throw new Error(`Research validation failed: ${error.stderr?.toString().trim() || error.message}`, { cause: error });
  }
}

export function prepareResearchReports(root) {
  validateResearch(root);
  try {
    execFileSync('make', ['reports'], {
      cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 120_000,
    });
  } catch (error) {
    throw new Error(`Report regeneration failed: ${error.stderr?.toString().trim() || error.message}`, { cause: error });
  }
}
