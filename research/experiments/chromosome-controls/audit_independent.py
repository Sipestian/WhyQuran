"""Read-only independent audit. Does not import run.py or quran_research.

Reads the frozen protocol and raw Tanzil bytes; emits a JSON report to stdout.
--artifacts permits checking a temporary copy for negative validation tests.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = Path(__file__).resolve().parent
COMMIT = 'eacece6f9cc3a0f5782457db542e0e6336477eea'
PROTOCOL_HASHES = {
    'protocol.json': '9be400bbd565dc7b173c3b4083277d27f4cdac2368267240c13e3f5161c2d50b',
    'protocol.md': '069bf721b04c5414a02255fb463b481c99cf2c59db1b126f7456bf4df0678744',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(directory):
    def read(name):
        return json.loads((directory / name).read_text())

    protocol = read('protocol.json')
    manifest = read('run-manifest.json')
    for name, expected in PROTOCOL_HASHES.items():
        raw = (directory / name).read_bytes()
        require(digest(raw) == expected, f'frozen {name}')
        committed = subprocess.check_output(
            ['git', 'show', f'{COMMIT}:research/experiments/chromosome-controls/{name}'], cwd=ROOT)
        require(raw == committed, f'commit {name}')
        require(manifest[name.replace('.', '_') + '_sha256'] == expected, f'manifest {name}')
    require(manifest['protocol_commit'] == COMMIT, 'manifest commit')
    settings = protocol['sampling']
    require((platform.python_implementation(), platform.python_version(), unicodedata.unidata_version)
            == (settings['python_implementation'], settings['python_version'], settings['unicode_version']),
            'Python/Unicode version differs from protocol')
    require(manifest['python_version'] == platform.python_version(), 'manifest Python version')
    require(manifest['unicode_version'] == unicodedata.unidata_version, 'manifest Unicode version')
    require(manifest['seed'] == settings['seed'] and manifest['replicates'] == settings['replicates'], 'manifest sampling')
    require(manifest['protocol_deviations'] == [], 'unreviewed protocol deviation')
    checked_hashes = {}
    for filename, claimed in manifest['artifact_hashes'].items():
        actual = digest((directory / filename).read_bytes())
        require(actual == claimed, f'artifact hash {filename}')
        checked_hashes[filename] = actual
    require(set(checked_hashes) == {'draws.jsonl', 'summary.json', 'pools.json', 'validation.json'}, 'artifact coverage')
    for name, key in [('run.py', 'script_sha256'), ('test_run.py', 'test_script_sha256')]:
        require(digest((directory / name).read_bytes()) == manifest[key], f'script hash {name}')

    metadata = protocol['inputs']['metadata']
    xml = (ROOT / metadata['path']).read_bytes()
    require(digest(xml) == metadata['sha256'] == manifest['metadata_sha256'], 'metadata hash')
    chapters = ET.fromstring(xml).findall('./suras/sura')
    expected_refs = [f'{int(ch.attrib["index"])}:{i}' for ch in chapters
                     for i in range(1, int(ch.attrib['ayas']) + 1)]
    require(len(chapters) == 114 and len(expected_refs) == 6236, 'metadata coverage')
    texts = {}
    stripped = {}
    prefixes = {'simple-clean': 'بسم الله الرحمن الرحيم',
                'uthmani': 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ'}
    for corpus, spec in protocol['inputs']['corpora'].items():
        raw = (ROOT / spec['path']).read_bytes()
        require(digest(raw) == spec['sha256'] == manifest['source_hashes'][corpus], f'source {corpus}')
        parsed = {}
        basmala_count = 0
        for line in raw.decode('utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split('|', 2)
            require(len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit(), 'unexpected source line')
            surah, ayah = map(int, fields[:2])
            ref = f'{surah}:{ayah}'
            require(ref not in parsed, f'duplicate {ref}')
            text = fields[2]
            if ayah == 1 and surah not in (1, 9):
                opening, remainder = ' '.join(text.split()[:4]), text.split(maxsplit=4)[4]
                allowed_openings = {prefixes[corpus]}
                if corpus == 'uthmani':
                    # The immutable source uses this joined-reading form at 95:1 and 97:1.
                    allowed_openings.add('بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ')
                require(opening in allowed_openings, f'opening basmala {corpus}/{ref}')
                text = remainder
                basmala_count += 1
            parsed[ref] = text
        require(list(parsed) == expected_refs, f'source coverage/order {corpus}')
        require(basmala_count == 112, f'basmala count {corpus}')
        require(parsed['1:1'] == prefixes[corpus], 'numbered basmala removed')
        require(prefixes[corpus] in parsed['27:30'], '27:30 basmala removed')
        texts[corpus] = parsed
        stripped[corpus] = basmala_count

    counts = {}
    for rule in protocol['count_rules']:
        rule_id = rule['id']
        allowed = rule.get('allowed_characters')
        counts[rule_id] = {}
        for ref, text in texts[rule['corpus']].items():
            frequencies = Counter(text)
            alphabet = set(allowed) if allowed is not None else {
                ch for ch in frequencies if ch != '\u0640' and unicodedata.category(ch) in {'Lu', 'Ll', 'Lt', 'Lm', 'Lo'}}
            counts[rule_id][ref] = sum(frequencies[ch] for ch in alphabet)
    require(list(counts) == ['C0', 'C1', 'C2', 'C3'], 'rule coverage')
    groups = {}
    original_totals = {c: {} for c in counts}
    for group in ['A', 'B']:
        spec = protocol['original_groups'][group]
        hits = Counter()
        for ref, text in texts['simple-clean'].items():
            hits[ref] = sum(text.split().count(term) for term in spec['terms'])
        refs = [ref for ref, n in hits.items() if n]
        require(refs == spec['verse_refs'] and len(refs) == spec['verse_count'], f'original refs {group}')
        require(sum(hits.values()) == spec['occurrence_count'], f'original occurrences {group}')
        groups[group] = set(refs)
        for rule in counts:
            total = sum(counts[rule][ref] for ref in refs)
            require(total == protocol['original_groups']['known_totals'][rule][group], f'original total {rule}/{group}')
            original_totals[rule][group] = total
    require(groups['A'] & groups['B'] == set(protocol['original_groups']['overlap_refs']), 'original overlap')
    original = groups['A'] | groups['B']
    slots = protocol['slots']
    require([s['original_ref'] for s in slots] == sorted(original, key=lambda r: tuple(map(int, r.split(':')))), 'slot ordering')
    for s in slots:
        ref = s['original_ref']
        membership = 'shared' if ref in groups['A'] & groups['B'] else ('A_only' if ref in groups['A'] else 'B_only')
        require(s['membership'] == membership, f'original membership {ref}')
        require(s['original_C0_length'] == counts['C0'][ref], f'slot length {ref}')
        require(s['length_bin'] == counts['C0'][ref] // 20, f'slot bin {ref}')

    bins = settings['bin_order']
    indices = {k: [i for i, s in enumerate(slots) if s['length_bin'] == k] for k in bins}
    pools = {k: [ref for ref in expected_refs if ref not in original and counts['C0'][ref] // 20 == k] for k in bins}
    saved_pools = read('pools.json')
    notice = (ROOT / 'data/SOURCE-LICENSE.txt').read_text()
    require(saved_pools['source_notice'] == manifest['source_notice'] == notice, 'source notice')
    pool_descriptions = []
    for k in bins:
        require(len(pools[k]) >= len(indices[k]), f'insufficient pool {k}')
        pool_descriptions.append({'bin_id': k, 'bounds': [20*k, 20*k+19], 'required': len(indices[k]),
                                  'size': len(pools[k]), 'verses': [{'ref': ref, 'C0_length': counts['C0'][ref]} for ref in pools[k]],
                                  'refs_sha256': digest(('\n'.join(pools[k]) + '\n').encode())})
    require(saved_pools['pools'] == pool_descriptions, 'complete pool reconstruction')

    rng = random.Random(settings['seed'])
    totals_seen = {c: {'A': [], 'B': []} for c in counts}
    hits_seen = {c: Counter() for c in counts}
    rule_histogram = Counter({str(i): 0 for i in range(5)})
    matched_draws = {c: [] for c in counts}
    checked = 0
    replay_digest = hashlib.sha256()
    with (directory / 'draws.jsonl').open() as stream:
        for line in stream:
            checked += 1
            require(checked <= settings['replicates'], 'too many draws')
            refs = [''] * len(slots)
            for k in bins:
                selected = rng.sample(pools[k], len(indices[k]))
                selected.sort(key=lambda r: tuple(map(int, r.split(':'))))
                rng.shuffle(selected)
                for idx, ref in zip(indices[k], selected):
                    refs[idx] = ref
            replay_digest.update((' '.join(refs) + '\n').encode())
            row = json.loads(line)
            require(row['replicate_id'] == checked, f'draw numbering {checked}')
            require(row['slot_refs'] == refs, f'replay at draw {checked}')
            a = [ref for i, ref in enumerate(refs) if slots[i]['membership'] in ['A_only', 'shared']]
            b = [ref for i, ref in enumerate(refs) if slots[i]['membership'] in ['B_only', 'shared']]
            require((len(a), len(b), len(set(a) & set(b)), len(set(refs))) == (12, 5, 3, 14), f'membership {checked}')
            require(not set(refs) & original, f'original included {checked}')
            require(all(counts['C0'][ref] // 20 == s['length_bin'] for ref, s in zip(refs, slots)), f'stratum {checked}')
            sums = {c: {'A': sum(counts[c][ref] for ref in a), 'B': sum(counts[c][ref] for ref in b)} for c in counts}
            require(row['totals_by_rule'] == sums, f'totals at draw {checked}')
            rests = {c: {g: {str(divisor): total % divisor for divisor in (23, 46)} for g, total in pair.items()} for c, pair in sums.items()}
            require(row['remainders_by_rule'] == rests, f'remainders at draw {checked}')
            flags = {}
            for c, pair in sums.items():
                a46, b46 = pair['A'] % 46 == 0, pair['B'] % 46 == 0
                both23 = pair['A'] % 23 == pair['B'] % 23 == 0
                flags[c] = {'A_divisible_by_46': a46, 'B_divisible_by_46': b46, 'both_divisible_by_46': a46 and b46,
                            'both_divisible_by_23': both23, 'both_divisible_by_23_but_not_both_by_46': both23 and not (a46 and b46)}
                require(not (a46 and b46) or both23, '46 not subset of 23')
                hits_seen[c].update({event: int(value) for event, value in flags[c].items()})
                for group in ['A', 'B']:
                    totals_seen[c][group].append(pair[group])
                if a46 and b46:
                    matched_draws[c].append(checked)
            require(row['event_flags'] == flags, f'flags at draw {checked}')
            rule_histogram[str(sum(f['both_divisible_by_46'] for f in flags.values()))] += 1
    n = settings['replicates']
    require(checked == n, f'expected {n} draws, found {checked}')
    summary = read('summary.json')
    for c in counts:
        expected_events = {event: {'count': value, 'denominator': n, 'fraction': value/n} for event, value in hits_seen[c].items()}
        distributions = {}
        for group, values in totals_seen[c].items():
            ordered = sorted(values)
            distributions[group] = {'min': ordered[0], 'median': (ordered[(n-1)//2] + ordered[n//2])/2, 'max': ordered[-1]}
        require(summary['rules'][c] == {'original_totals': original_totals[c], 'events': expected_events, 'sum_distribution': distributions}, f'summary rule {c}')
    require(summary['primary'] == {'rule': 'C3', 'divisor': 46, 'event': 'both_groups', 'count': len(matched_draws['C3']), 'denominator': n, 'fraction': len(matched_draws['C3'])/n}, 'primary summary')
    require(summary['number_of_jointly_matching_rules_histogram'] == rule_histogram, 'summary histogram')
    for field, amount in [('any_rule_joint46', n-rule_histogram['0']), ('all_rules_joint46', rule_histogram['4'])]:
        require(summary[field] == {'count': amount, 'denominator': n, 'fraction': amount/n}, f'summary {field}')
    require(summary['pool_summary'] == [{key: pool[key] for key in ['bin_id', 'bounds', 'required', 'size']} for pool in pool_descriptions], 'summary pools')
    require(summary['source_notice'] == notice, 'summary notice')
    require(summary['protocol_sha256'] == PROTOCOL_HASHES['protocol.json'] and summary['protocol_commit'] == COMMIT, 'summary provenance')
    require(summary['replicates'] == n and summary['seed'] == settings['seed'], 'summary sampling')
    validation = read('validation.json')
    require(validation['status'] == 'passed' and validation['draws_checked'] == n, 'internal validation result')
    return {'status': 'passed', 'reader_id': 'family_law_reading', 'independent_of_run_py_and_corpus_module': True,
            'checked_draws': checked, 'replay_refs_sha256': replay_digest.hexdigest(), 'original_totals': original_totals,
            'basmalas_removed_per_corpus': stripped, 'pool_sizes': {str(k): len(pools[k]) for k in bins},
            'joint_46_counts': {c: len(ids) for c, ids in matched_draws.items()}, 'joint_46_replicate_ids': matched_draws,
            'rule_match_histogram': dict(rule_histogram), 'protocol_commit': COMMIT, 'artifact_hashes': checked_hashes,
            'audit_script_sha256': digest(Path(__file__).read_bytes()), 'python_version': platform.python_version(),
            'unicode_version': unicodedata.unidata_version,
            'scope_ar': 'إعادة حساب مستقلة من المصدرين ومطابقة جميع الأحواض والسحوبات والمجاميع والبواقي والجداول؛ لا تثبت صلاحية المرجع لاستدلال عن قصد النص.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=DEFAULT)
    options = parser.parse_args()
    try:
        result = audit(options.artifacts)
    except (ValueError, KeyError, OSError, IndexError) as error:
        print(f'Audit failed: {error}', file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
