"""Execute the frozen, descriptive chromosome controls using only the stdlib."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from quran_research.corpus import BASMALAS, load_corpus, verify_sources

COMMIT = 'eacece6f9cc3a0f5782457db542e0e6336477eea'
FROZEN = {'protocol.json': '9be400bbd565dc7b173c3b4083277d27f4cdac2368267240c13e3f5161c2d50b',
          'protocol.md': '069bf721b04c5414a02255fb463b481c99cf2c59db1b126f7456bf4df0678744'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def ref_key(ref):
    return tuple(map(int, ref.split(':')))


def analysis_text(ref, text):
    surah, ayah = ref_key(ref)
    tokens = text.split()
    if ayah == 1 and surah not in (1, 9):
        if tuple(tokens[:4]) not in BASMALAS:
            raise ValueError(f'Unexpected basmala: {ref}')
        return ' '.join(tokens[4:])
    return text


def count_verse(texts, rules):
    result = {}
    for rule in rules:
        text = texts[rule['corpus']]
        if 'allowed_characters' in rule:
            allowed = set(rule['allowed_characters'])
            result[rule['id']] = sum(c in allowed for c in text)
        else:
            result[rule['id']] = sum(c != '\u0640' and unicodedata.category(c).startswith('L') for c in text)
    return result


def make_pools(lengths, slots):
    originals = {s['original_ref'] for s in slots}
    bins = sorted({s['length_bin'] for s in slots})
    return {k: sorted((r for r, n in lengths.items() if r not in originals and n // 20 == k), key=ref_key)
            for k in bins}


def draw_refs(protocol, pools, replicates=None):
    slots = protocol['slots']
    by_bin = {k: [i for i, s in enumerate(slots) if s['length_bin'] == k]
              for k in protocol['sampling']['bin_order']}
    # Validate every bin before consuming any randomness or yielding any draw.
    for k, indices in by_bin.items():
        if len(pools[k]) < len(indices):
            raise ValueError(f'insufficient pool {k}: {len(pools[k])} < {len(indices)}')
    rng = random.Random(protocol['sampling']['seed'])
    n = protocol['sampling']['replicates'] if replicates is None else replicates
    for _ in range(n):
        refs = [None] * len(slots)
        for k, indices in by_bin.items():
            selected = sorted(rng.sample(pools[k], len(indices)), key=ref_key)
            rng.shuffle(selected)
            for i, ref in zip(indices, selected):
                refs[i] = ref
        yield refs


def group_refs(refs, slots):
    return ([r for r, s in zip(refs, slots) if s['membership'] != 'B_only'],
            [r for r, s in zip(refs, slots) if s['membership'] != 'A_only'])


def events(totals):
    a, b = totals['A'], totals['B']
    both46 = a % 46 == 0 and b % 46 == 0
    both23 = a % 23 == 0 and b % 23 == 0
    return {'A_divisible_by_46': a % 46 == 0, 'B_divisible_by_46': b % 46 == 0,
            'both_divisible_by_46': both46, 'both_divisible_by_23': both23,
            'both_divisible_by_23_but_not_both_by_46': both23 and not both46}


def row_for(replicate_id, refs, slots, counts):
    a, b = group_refs(refs, slots)
    totals = {c: {'A': sum(counts[r][c] for r in a), 'B': sum(counts[r][c] for r in b)}
              for c in ('C0', 'C1', 'C2', 'C3')}
    return {'replicate_id': replicate_id, 'slot_refs': refs, 'totals_by_rule': totals,
            'remainders_by_rule': {c: {g: {'23': v % 23, '46': v % 46} for g, v in t.items()}
                                   for c, t in totals.items()},
            'event_flags': {c: events(t) for c, t in totals.items()}}


def prepare_inputs(protocol):
    for name, expected in FROZEN.items():
        raw = (HERE / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError(f'Frozen protocol changed: {name}')
        path = str((HERE / name).relative_to(ROOT))
        committed = subprocess.check_output(['git', 'show', f'{COMMIT}:{path}'], cwd=ROOT)
        if committed != raw:
            raise ValueError(f'Protocol does not match frozen commit: {name}')
    env = protocol['sampling']
    if (platform.python_implementation(), platform.python_version(), unicodedata.unidata_version) != (
            env['python_implementation'], env['python_version'], env['unicode_version']):
        raise ValueError('Python/Unicode environment differs from frozen protocol')
    verify_sources(ROOT)
    for spec in [*protocol['inputs']['corpora'].values(), protocol['inputs']['metadata']]:
        if sha((ROOT / spec['path']).read_bytes()) != spec['sha256']:
            raise ValueError(f"Frozen source changed: {spec['path']}")
    corpora = {c: {v.ref: analysis_text(v.ref, v.text) for v in load_corpus(ROOT, c)}
               for c in ('simple-clean', 'uthmani')}
    if set(corpora['simple-clean']) != set(corpora['uthmani']):
        raise ValueError('Corpus references differ')
    counts = {r: count_verse({c: corpus[r] for c, corpus in corpora.items()}, protocol['count_rules'])
              for r in corpora['simple-clean']}
    for group in ('A', 'B'):
        spec = protocol['original_groups'][group]
        found = [r for r, text in corpora['simple-clean'].items() if set(text.split()) & set(spec['terms'])]
        occurrences = sum(w in spec['terms'] for text in corpora['simple-clean'].values() for w in text.split())
        if found != spec['verse_refs'] or occurrences != spec['occurrence_count']:
            raise ValueError(f'Original group changed: {group}')
        for c, totals in protocol['original_groups']['known_totals'].items():
            if sum(counts[r][c] for r in found) != totals[group]:
                raise ValueError(f'Original total changed: {group}/{c}')
    for slot in protocol['slots']:
        if counts[slot['original_ref']]['C0'] != slot['original_C0_length']:
            raise ValueError(f"Original slot length changed: {slot['slot_id']}")
    return corpora, counts


def validate_saved(protocol, pools, corpora, counts):
    # A second character-count path uses frequencies rather than a character loop.
    independent = {}
    for r in corpora['simple-clean']:
        independent[r] = {}
        for rule in protocol['count_rules']:
            frequency = Counter(corpora[rule['corpus']][r])
            allowed = rule.get('allowed_characters')
            if allowed is None:
                allowed = {c for c in frequency if unicodedata.category(c) in ('Lu', 'Ll', 'Lt', 'Lm', 'Lo') and c != '\u0640'}
            independent[r][rule['id']] = sum(frequency[c] for c in set(allowed))
    if independent != counts:
        raise ValueError('Independent character counts differ')
    original = {s['original_ref'] for s in protocol['slots']}
    replay = draw_refs(protocol, pools)
    checked = 0
    with (HERE / 'draws.jsonl').open() as stream:
        for checked, line in enumerate(stream, 1):
            row = json.loads(line)
            refs = row['slot_refs']
            if refs != next(replay):
                raise ValueError(f'Seed replay differs at draw {checked}')
            a, b = group_refs(refs, protocol['slots'])
            if (len(refs), len(set(refs)), len(a), len(b), len(set(a) & set(b))) != (14, 14, 12, 5, 3):
                raise ValueError(f'Invalid membership at draw {checked}')
            if set(refs) & original:
                raise ValueError(f'Original verse sampled at draw {checked}')
            if any(counts[r]['C0'] // 20 != s['length_bin'] for r, s in zip(refs, protocol['slots'])):
                raise ValueError(f'Length stratum mismatch at draw {checked}')
            if row != row_for(checked, refs, protocol['slots'], independent):
                raise ValueError(f'Saved results differ at draw {checked}')
            if any(f['both_divisible_by_46'] and not f['both_divisible_by_23'] for f in row['event_flags'].values()):
                raise ValueError('46 event is not contained in 23 event')
    if checked != protocol['sampling']['replicates'] or next(replay, None) is not None:
        raise ValueError('Wrong number of saved draws')
    return {'status': 'passed', 'draws_checked': checked, 'full_seed_replay': True,
            'independent_character_recount': True, 'all_saved_results_recomputed': True,
            'membership_overlap_exclusion_and_strata': True, 'nested_23_46_events': True,
            'note_ar': 'تحقق برمجي داخلي كامل؛ المراجعة المستقلة مطلوبة قبل النشر، ولا يثبت صلاحية مرجع لغوي أو قصد نصي.'}


def main():
    started = datetime.now(timezone.utc).isoformat()
    protocol = json.loads((HERE / 'protocol.json').read_text())
    corpora, counts = prepare_inputs(protocol)
    lengths = {r: c['C0'] for r, c in counts.items()}
    pools = make_pools(lengths, protocol['slots'])
    required = Counter(s['length_bin'] for s in protocol['slots'])
    for k in pools:
        if len(pools[k]) < required[k]:
            raise ValueError(f'insufficient pool {k}: {len(pools[k])} < {required[k]}')
    notice = (ROOT / 'data/SOURCE-LICENSE.txt').read_text()
    pool_data = [{'bin_id': k, 'bounds': [20*k, 20*k+19], 'required': required[k], 'size': len(pool),
                  'verses': [{'ref': r, 'C0_length': lengths[r]} for r in pool],
                  'refs_sha256': sha(('\n'.join(pool) + '\n').encode())} for k, pool in pools.items()]
    write_json('pools.json', {'source_notice': notice, 'pools': pool_data})
    events_by_rule = {c: Counter() for c in ('C0', 'C1', 'C2', 'C3')}
    sums = {c: {'A': [], 'B': []} for c in events_by_rule}
    rule_histogram = Counter({i: 0 for i in range(5)})
    n = protocol['sampling']['replicates']
    with (HERE / 'draws.jsonl').open('w') as stream:
        for i, refs in enumerate(draw_refs(protocol, pools), 1):
            row = row_for(i, refs, protocol['slots'], counts)
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            for c in events_by_rule:
                events_by_rule[c].update({k: int(v) for k, v in row['event_flags'][c].items()})
                for g in ('A', 'B'):
                    sums[c][g].append(row['totals_by_rule'][c][g])
            rule_histogram[sum(f['both_divisible_by_46'] for f in row['event_flags'].values())] += 1
    hits = events_by_rule['C3']['both_divisible_by_46']
    print(json.dumps({'primary_C3_both_divisible_by_46': hits, 'replicates': n, 'fraction': hits/n,
                      'pool_sizes': {k: len(v) for k, v in pools.items()}}, ensure_ascii=False), flush=True)
    summary = {'id': protocol['id'], 'kind': 'descriptive_reference_comparison', 'source_notice': notice,
               'protocol_commit': COMMIT, 'protocol_sha256': FROZEN['protocol.json'], 'seed': protocol['sampling']['seed'],
               'replicates': n, 'primary': {'rule': 'C3', 'divisor': 46, 'event': 'both_groups', 'count': hits,
                                          'denominator': n, 'fraction': hits/n},
               'rules': {}, 'number_of_jointly_matching_rules_histogram': dict(rule_histogram),
               'any_rule_joint46': {'count': n-rule_histogram[0], 'denominator': n, 'fraction': (n-rule_histogram[0])/n},
               'all_rules_joint46': {'count': rule_histogram[4], 'denominator': n, 'fraction': rule_histogram[4]/n},
               'pool_summary': [{k: b[k] for k in ('bin_id','bounds','required','size')} for b in pool_data],
               'interpretation_ar': 'نسب وصفية داخل المرجع المثبت؛ ليست احتمال المعجزة أو المصادفة، ولا تمثل طريقة اختيار ألفاظ صاحب الدعوى.',
               'limitations_ar': protocol['limitations_ar']}
    for c, values in events_by_rule.items():
        summary['rules'][c] = {'original_totals': protocol['original_groups']['known_totals'][c],
                              'events': {k: {'count': v, 'denominator': n, 'fraction': v/n} for k, v in values.items()},
                              'sum_distribution': {g: {'min': min(v), 'median': statistics.median(v), 'max': max(v)} for g, v in sums[c].items()}}
    validation = validate_saved(protocol, pools, corpora, counts)
    write_json('validation.json', validation)
    write_json('summary.json', summary)
    manifest = {'protocol_commit': COMMIT, 'protocol_json_sha256': FROZEN['protocol.json'], 'protocol_md_sha256': FROZEN['protocol.md'],
                'source_hashes': {k: v['sha256'] for k, v in protocol['inputs']['corpora'].items()},
                'metadata_sha256': protocol['inputs']['metadata']['sha256'], 'python_version': platform.python_version(),
                'unicode_version': unicodedata.unidata_version, 'rng': protocol['sampling']['rng'], 'seed': protocol['sampling']['seed'],
                'replicates': n, 'started_at_utc': started, 'completed_at_utc': datetime.now(timezone.utc).isoformat(),
                'script_sha256': sha(Path(__file__).read_bytes()), 'test_script_sha256': sha((HERE/'test_run.py').read_bytes()),
                'artifact_hashes': {name: sha((HERE/name).read_bytes()) for name in ('pools.json','draws.jsonl','summary.json','validation.json')},
                'source_notice': notice, 'protocol_deviations': []}
    write_json('run-manifest.json', manifest)
    print(json.dumps(validation, ensure_ascii=False))


if __name__ == '__main__':
    main()
