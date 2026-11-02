import copy
import unittest

from quran_research.corpus import parse_text
from quran_research.catalog import validate_annotations


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.verses = parse_text('1|1|نور نور\n1|2|الله\n2|1|بسم الله الرحمن الرحيم نور\n')
        self.annotation = {
            'corpus': 'simple-clean', 'corpus_sha256': 'fixed-source',
            'include_opening_basmalas': False,
            'queries': [{'id': 'light', 'title_ar': 'نور', 'terms': ['نور'], 'scope_note_ar': 'الاسم وحده'}],
            'occurrences': [
                {'query_id': 'light', 'verse_ref': '1:1', 'source_word_position': 1, 'source_token': 'نور'},
                {'query_id': 'light', 'verse_ref': '1:1', 'source_word_position': 2, 'source_token': 'نور'},
                {'query_id': 'light', 'verse_ref': '2:1', 'source_word_position': 5, 'source_token': 'نور'},
            ],
        }

    def check(self, annotation):
        return validate_annotations(annotation, self.verses, 'fixed-source')

    def test_complete_occurrences_preserve_original_source_positions(self):
        self.check(self.annotation)

    def test_missing_duplicate_and_wrong_positions_are_rejected(self):
        bad = copy.deepcopy(self.annotation)
        bad['occurrences'].pop()
        with self.assertRaises(ValueError):
            self.check(bad)
        bad = copy.deepcopy(self.annotation)
        bad['occurrences'].append(bad['occurrences'][0])
        with self.assertRaises(ValueError):
            self.check(bad)
        for key, value in [('source_word_position', 1), ('verse_ref', '2:2'), ('source_token', 'النور'), ('query_id', 'other')]:
            bad = copy.deepcopy(self.annotation)
            bad['occurrences'][-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(bad)

    def test_wrong_source_and_ambiguous_policy_are_rejected(self):
        for key, value in [('corpus', 'uthmani'), ('corpus_sha256', 'different'), ('include_opening_basmalas', 'false')]:
            bad = dict(self.annotation, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(bad)
        bad = copy.deepcopy(self.annotation)
        bad['occurrences'][0]['source_word_position'] = True
        with self.assertRaises(ValueError):
            self.check(bad)

    def test_overlapping_queries_require_separate_complete_coverage(self):
        annotation = copy.deepcopy(self.annotation)
        annotation['queries'].append(dict(annotation['queries'][0], id='comparison'))
        with self.assertRaises(ValueError):
            self.check(annotation)
        annotation['occurrences'] += [dict(row, query_id='comparison') for row in self.annotation['occurrences']]
        self.check(annotation)

    def test_newly_declared_form_requires_its_occurrences(self):
        annotation = copy.deepcopy(self.annotation)
        annotation['queries'][0]['terms'].append('الله')
        with self.assertRaises(ValueError):
            self.check(annotation)

    def test_semantic_labels_are_not_claimed_as_machine_verified(self):
        annotation = copy.deepcopy(self.annotation)
        annotation['occurrences'][0]['uncertainty_ar'] = 'تصنيف دلالي يحتاج مراجعة بشرية مستقلة.'
        self.check(annotation)

    def test_registered_query_cannot_silently_describe_a_different_scope(self):
        registry = copy.deepcopy(self.annotation['queries'])
        validate_annotations(self.annotation, self.verses, 'fixed-source', registry)
        for field, value in [('terms', ['النور']), ('surah', 1), ('include_opening_basmalas', True), ('id', 'missing')]:
            changed = [dict(registry[0], **{field: value})]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_annotations(self.annotation, self.verses, 'fixed-source', changed)


if __name__ == '__main__':
    unittest.main()
