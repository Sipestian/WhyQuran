import unittest
from pathlib import Path
import hashlib
import json
import shutil
import tempfile

from quran_research.corpus import parse_text, count_matches, concordance, load_corpus, word_inventory, character_inventory


ROOT = Path(__file__).resolve().parents[1]


class CorpusTests(unittest.TestCase):
    def test_character_inventory_does_not_silently_merge_hamza_or_drop_marks(self):
        verses = parse_text('1|1|آ أ أ اَـ\n')
        result = character_inventory(verses)
        chars = {c['character']: c['count'] for c in result['characters']}
        self.assertEqual(chars, {'آ': 1, 'ا': 2, 'ٔ': 1, 'أ': 1, 'َ': 1, 'ـ': 1})
        self.assertEqual(result['non_whitespace_codepoints'], 7)
        self.assertEqual(result['letter_codepoints_excluding_tatweel'], 4)
        self.assertEqual(result['mark_codepoints'], 2)

    def test_character_inventory_obeys_numbered_basmala_policy(self):
        verses = parse_text('1|1|بسم الله الرحمن الرحيم\n2|1|بسم الله الرحمن الرحيم الم\n')
        without = character_inventory(verses)
        with_openings = character_inventory(verses, include_opening_basmalas=True)
        self.assertEqual(without['non_whitespace_codepoints'], 22)
        self.assertEqual(with_openings['non_whitespace_codepoints'], 41)

    def test_word_inventory_keeps_forms_separate_and_source_positions(self):
        verses = parse_text('1|1|يوم اليوم يوم\n2|1|بسم الله الرحمن الرحيم يوم\n')
        index = {entry['word']: entry for entry in word_inventory(verses)}
        self.assertEqual(index['يوم']['count'], 3)
        self.assertEqual(index['اليوم']['count'], 1)
        self.assertEqual(index['يوم']['locations'], [['1:1', 1], ['1:1', 3], ['2:1', 5]])
        self.assertNotIn('بسم', index)

    def test_exact_tokens_not_substrings_or_implicit_roots(self):
        verses = parse_text('1|1|يوم يومئذ اليوم يوما يوم\n')
        result = count_matches(verses, ['يوم'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['matches'][0]['token_positions'], [1, 5])

    def test_duplicate_terms_do_not_double_count(self):
        verses = parse_text('1|1|يوم اليوم\n')
        self.assertEqual(count_matches(verses, ['يوم', 'يوم'])['count'], 1)

    def test_phrase_repetitions_count_and_never_cross_verses(self):
        verses = parse_text('1|1|أ ب أ ب\n1|2|ج أ\n1|3|ب ج\n')
        self.assertEqual(count_matches(verses, ['أ ب'])['count'], 2)

    def test_opening_basmala_policy_keeps_numbered_and_embedded(self):
        verses = parse_text('1|1|بسم الله الرحمن الرحيم\n2|1|بسم الله الرحمن الرحيم الم\n9|1|براءة من الله ورسوله\n27|30|إنه من سليمان وإنه بسم الله الرحمن الرحيم\n')
        self.assertEqual(count_matches(verses, ['بسم الله الرحمن الرحيم'])['count'], 2)
        self.assertEqual(count_matches(verses, ['بسم الله الرحمن الرحيم'], include_opening_basmalas=True)['count'], 3)

    def test_token_positions_still_point_to_original_source(self):
        verses = parse_text('2|1|بسم الله الرحمن الرحيم الم\n')
        result = count_matches(verses, ['الم'])
        self.assertEqual(result['matches'][0]['token_positions'], [5])

    def test_uthmani_opening_basmala(self):
        verses = parse_text('2|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ الٓمٓ\n')
        self.assertEqual(count_matches(verses, ['بِسْمِ'])['count'], 0)

    def test_uthmani_assimilated_basmala_in_tin_and_qadr(self):
        verses = parse_text('95|1|بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ وَٱلتِّينِ وَٱلزَّيْتُونِ\n97|1|بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ إِنَّآ\n')
        self.assertEqual(count_matches(verses, ['بِّسْمِ'])['count'], 0)
        self.assertEqual(count_matches(verses, ['بِّسْمِ'], include_opening_basmalas=True)['count'], 2)

    def test_full_uthmani_corpus_is_accepted_without_modification(self):
        self.assertEqual(len(load_corpus(ROOT, 'uthmani')), 6236)

    def test_changed_source_is_rejected_before_counting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'data', root / 'data')
            source = root / 'data/source/tanzil-simple-clean.txt'
            source.write_bytes(source.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'تغير ملف المصدر'):
                load_corpus(root)

    def test_missing_verse_rejected_even_with_updated_file_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'data', root / 'data')
            source = root / 'data/source/tanzil-simple-clean.txt'
            source.write_text(''.join(line for line in source.read_text().splitlines(keepends=True) if not line.startswith('2|286|')))
            manifest_path = root / 'data/manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['files'][source.name]['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest['files'][source.name]['bytes'] = source.stat().st_size
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'تغطية الآيات'):
                load_corpus(root)

    def test_empty_terms_and_bad_surah_rejected(self):
        verses = parse_text('1|1|نص\n')
        for terms in [[], [''], ['   ']]:
            with self.assertRaises(ValueError):
                count_matches(verses, terms)
        with self.assertRaises(ValueError):
            count_matches(verses, ['نص'], surah=115)

    def test_invalid_types_cannot_silently_change_counting_rules(self):
        verses = parse_text('2|1|بسم الله الرحمن الرحيم نص\n')
        with self.assertRaises(ValueError):
            count_matches(verses, 'نص')
        with self.assertRaises(ValueError):
            count_matches(verses, ['نص'], include_opening_basmalas='false')
        with self.assertRaises(ValueError):
            count_matches(verses, ['نص'], surah=True)

    def test_duplicate_and_malformed_rows_rejected(self):
        for text in ['1|1|أ\n1|1|ب', '1|1|', 'html error', '0|1|نص', '2|2|أ\n2|1|ب']:
            with self.assertRaises(ValueError):
                parse_text(text)

    def test_context_stays_in_surah_and_preserves_raw_text(self):
        verses = parse_text('1|1|أ\n1|2|يوم\n2|1|بسم الله الرحمن الرحيم ب\n')
        result = concordance(verses, ['يوم'], radius=1)
        self.assertEqual([v['ref'] for v in result['matches'][0]['context']], ['1:1', '1:2'])
        self.assertEqual(result['matches'][0]['text'], 'يوم')

    def test_full_corpus_and_independent_refrain_positions(self):
        verses = load_corpus(ROOT)
        self.assertEqual(len(verses), 6236)
        result = count_matches(verses, ['فبأي آلاء ربكما تكذبان'], surah=55)
        self.assertEqual(result['count'], 31)
        self.assertEqual([m['ref'] for m in result['matches']], [f'55:{n}' for n in [13,16,18,21,23,25,28,30,32,34,36,38,40,42,45,47,49,51,53,55,57,59,61,63,65,67,69,71,73,75,77]])


if __name__ == '__main__':
    unittest.main()
