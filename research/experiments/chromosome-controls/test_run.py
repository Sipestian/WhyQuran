"""Focused checks for the frozen chromosome comparison; no site/report mutation."""
import importlib.util
import json
import random
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('chromosome_controls_run', HERE / 'run.py')
MOD = None
if (HERE / 'run.py').exists():
    MOD = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MOD)
PROTOCOL = json.loads((HERE / 'protocol.json').read_text())


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(MOD, 'The experiment implementation has not been written')

    def fixture(self):
        lengths = {}
        for bin_id in PROTOCOL['sampling']['bin_order']:
            for i in range(1, 11):
                lengths[f'{bin_id+100}:{i}'] = bin_id * 20 + 10
        return lengths, MOD.make_pools(lengths, PROTOCOL['slots'])

    def test_preserves_sizes_overlap_and_unique_verses(self):
        _, pools = self.fixture()
        for refs in MOD.draw_refs(PROTOCOL, pools, 30):
            a, b = MOD.group_refs(refs, PROTOCOL['slots'])
            self.assertEqual((len(refs), len(set(refs))), (14, 14))
            self.assertEqual((len(a), len(b), len(set(a) & set(b))), (12, 5, 3))

    def test_matches_each_slot_length_bin(self):
        lengths, pools = self.fixture()
        for refs in MOD.draw_refs(PROTOCOL, pools, 30):
            for slot, ref in zip(PROTOCOL['slots'], refs):
                self.assertEqual(lengths[ref] // 20, slot['length_bin'])

    def test_pool_excludes_all_original_refs_and_obeys_boundary(self):
        lengths, _ = self.fixture()
        lengths.update({s['original_ref']: s['original_C0_length'] for s in PROTOCOL['slots']})
        lengths.update({'114:1': 19, '114:2': 20, '114:3': 39, '114:4': 40})
        pools = MOD.make_pools(lengths, PROTOCOL['slots'])
        combined = {r for pool in pools.values() for r in pool}
        self.assertFalse(combined & {s['original_ref'] for s in PROTOCOL['slots']})
        self.assertIn('114:1', pools[0])
        self.assertIn('114:2', pools[1])
        self.assertIn('114:3', pools[1])
        self.assertIn('114:4', pools[2])

    def test_insufficient_pool_fails_before_first_draw(self):
        _, pools = self.fixture()
        pools[13] = []
        with self.assertRaisesRegex(ValueError, 'insufficient pool 13'):
            next(MOD.draw_refs(PROTOCOL, pools, 1))

    def test_seed_reproducibility_without_reusing_same_draw(self):
        _, pools = self.fixture()
        first = list(MOD.draw_refs(PROTOCOL, pools, 30))
        self.assertEqual(first, list(MOD.draw_refs(PROTOCOL, pools, 30)))
        self.assertGreater(len({tuple(r) for r in first}), 1)

    def test_basmala_policy_keeps_numbered_occurrences(self):
        basmala = 'بسم الله الرحمن الرحيم'
        self.assertEqual(MOD.analysis_text('1:1', basmala), basmala)
        self.assertEqual(MOD.analysis_text('27:30', 'إنه من سليمان وإنه ' + basmala), 'إنه من سليمان وإنه ' + basmala)
        self.assertEqual(MOD.analysis_text('2:1', basmala + ' الم'), 'الم')
        self.assertEqual(MOD.analysis_text('9:1', 'براءة من الله'), 'براءة من الله')
        with self.assertRaisesRegex(ValueError, 'basmala'):
            MOD.analysis_text('2:1', 'الم')

    def test_count_rules_discriminate_marks_small_letters_and_hamza(self):
        # ضمّة mark, small waw U+06E5 letter, standalone hamza, alif carrier, tatweel.
        texts = {'simple-clean': 'ءأـبُ', 'uthmani': 'ءأـبُۥ'}
        self.assertEqual(MOD.count_verse(texts, PROTOCOL['count_rules']), {'C0': 3, 'C1': 4, 'C2': 3, 'C3': 2})

    def test_23_event_is_dependent_subset(self):
        flags = MOD.events({'A': 46, 'B': 92})
        self.assertTrue(flags['both_divisible_by_46'])
        self.assertTrue(flags['both_divisible_by_23'])
        self.assertFalse(flags['both_divisible_by_23_but_not_both_by_46'])
        flags = MOD.events({'A': 23, 'B': 46})
        self.assertFalse(flags['both_divisible_by_46'])
        self.assertTrue(flags['both_divisible_by_23_but_not_both_by_46'])


if __name__ == '__main__':
    unittest.main()
