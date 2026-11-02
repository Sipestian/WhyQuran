import copy
import unittest

from quran_research.corpus import parse_text
from quran_research.catalog import validate_reading, validate_record, validate_queries, validate_query_links, universe_results


class CatalogTests(unittest.TestCase):
    def test_universe_groups_preserve_explicit_forms_and_semantic_caveats(self):
        verses = parse_text('1|1|السماء والسماوات\n1|2|السماء\n')
        groups = [{'id': 'sky', 'title_ar': 'السماء', 'terms': ['السماء'], 'scope_note_ar': 'المفرد فقط', 'semantic_caveats_ar': ['السياق يحدد المعنى'], 'excluded_candidate_forms': ['والسماوات']}]
        result = universe_results(verses, groups)
        self.assertEqual(result[0]['count'], 2)
        self.assertEqual(result[0]['semantic_caveats_ar'], ['السياق يحدد المعنى'])
        self.assertEqual(result[0]['excluded_candidate_forms'], ['والسماوات'])
        with self.assertRaises(ValueError):
            universe_results(verses, groups + groups)

    def test_expected_count_requires_nonnegative_integer(self):
        query = {'id': 'sample', 'title_ar': 'عنوان', 'terms': ['نص'], 'scope_note_ar': 'نطاق'}
        for invalid in [True, False, 1.0, '1', -1]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                validate_queries([dict(query, expected_count=invalid)])
        validate_queries([dict(query, expected_count=0)])

    def test_query_links_must_resolve_without_duplicates(self):
        for links in [['missing'], ['known', 'known'], 'known', [1]]:
            with self.subTest(links=links), self.assertRaises(ValueError):
                validate_query_links([{'id': 'claim', 'category': 'counts', 'query_ids': links}], {'known'})
        validate_query_links([{'id': 'claim', 'category': 'counts', 'query_ids': ['known']}], {'known'})
        with self.assertRaises(ValueError):
            validate_query_links([{'id': 'claim', 'category': 'counts'}], {'known'})

    def test_malformed_query_cannot_silently_broaden_scope(self):
        query = {'id': 'sample', 'title_ar': 'عنوان', 'terms': ['نص'], 'scope_note_ar': 'نطاق'}
        for extra in [{'surahs': 55}, {'terms': 'نص'}, {'include_opening_basmalas': 'false'}, {'surah': True}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_queries([dict(query, **extra)])

    def test_count_evidence_can_reference_a_generated_nonconcordance_report(self):
        record = {'id': 'letters', 'category': 'counts', 'report_ids': ['characters-simple-clean', 'characters-uthmani']}
        validate_query_links([record], set())
        for reports in [['missing'], ['characters-simple-clean', 'characters-simple-clean'], 'characters-simple-clean', [1]]:
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                validate_query_links([dict(record, report_ids=reports)], set())

    def setUp(self):
        self.verses = parse_text('1|1|أ\n1|2|ب\n2|1|ج\n')
        self.ledger = {'reader_id': 'reader', 'corpus_sha256': 'abc', 'method': 'model_visible_complete_text', 'completed': True, 'compaction_note_ar': 'لا ضمان لبقاء كل النص في سياق واحد.', 'blocks': [
            {'start_ref': '1:1', 'end_ref': '1:2', 'verse_count': 2, 'notes_ar': 'ملاحظة قراءة أولى'},
            {'start_ref': '2:1', 'end_ref': '2:1', 'verse_count': 1, 'notes_ar': 'ملاحظة قراءة ثانية'},
        ]}

    def test_complete_reading_accepted(self):
        validate_reading(self.ledger, self.verses, 'abc')

    def test_gaps_overlaps_wrong_hash_and_false_completion_rejected(self):
        bad = []
        for key, value in [('corpus_sha256', 'bad'), ('completed', False), ('method', 'file_loaded')]:
            ledger = copy.deepcopy(self.ledger)
            ledger[key] = value
            bad.append(ledger)
        ledger = copy.deepcopy(self.ledger); ledger['blocks'] = ledger['blocks'][:1]; bad.append(ledger)
        ledger = copy.deepcopy(self.ledger); ledger['blocks'].append(ledger['blocks'][1]); bad.append(ledger)
        ledger = copy.deepcopy(self.ledger); ledger['blocks'][0]['verse_count'] = 3; bad.append(ledger)
        ledger = copy.deepcopy(self.ledger); ledger['blocks'][0]['notes_ar'] = ''; bad.append(ledger)
        for ledger in bad:
            with self.subTest(ledger=ledger), self.assertRaises(ValueError):
                validate_reading(ledger, self.verses, 'abc')

    def test_record_requires_sources_valid_refs_and_completed_readers(self):
        record = {'id': 'test-record', 'title_ar': 'عنوان', 'category': 'wording', 'claim_ar': 'دعوى', 'observation_ar': 'ملاحظة', 'interpretation_ar': 'تفسير', 'status': 'documented_interpretation', 'verse_refs': ['1:1'], 'sources': [{'id': 's', 'title': 'مصدر', 'url': 'https://example.org/source', 'kind': 'tafsir', 'locator': '1:1', 'supports_ar': 'يسند الملاحظة', 'accessed_at': '2026-11-02'}], 'limitations_ar': ['حد'], 'next_questions_ar': ['سؤال'], 'baseline_ids': [], 'novelty': 'previously_published', 'reviewed_by': ['reader']}
        validate_record(record, self.verses, {'reader'})
        for key, value in [('verse_refs', ['2:2']), ('sources', []), ('reviewed_by', ['unread']), ('status', 'miracle_proved'), ('limitations_ar', [])]:
            bad = dict(record, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_record(bad, self.verses, {'reader'})


if __name__ == '__main__':
    unittest.main()
