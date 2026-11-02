"""التحقق من سجلات القراءة والأدلة وتجهيز بيانات الموقع المستقبلي."""

import json
from pathlib import Path
import re
from urllib.parse import urlparse

from .corpus import CORPORA, load_corpus, verify_sources, concordance, count_matches


STATUSES = {'documented_interpretation', 'scientific_comparison', 'reproduced_observation', 'hypothesis', 'needs_verification'}
CATEGORIES = {'wording', 'counts', 'science', 'family_law'}


def validate_queries(queries):
    if not isinstance(queries, list):
        raise ValueError('الاستعلامات يجب أن تكون قائمة')
    seen = set()
    allowed = {'id', 'title_ar', 'terms', 'scope_note_ar', 'surah', 'include_opening_basmalas', 'expected_count'}
    for query in queries:
        if not isinstance(query, dict) or set(query) - allowed:
            raise ValueError('حقول استعلام غير معروفة')
        for key in ['id', 'title_ar', 'scope_note_ar']:
            if not isinstance(query.get(key), str) or not query[key].strip():
                raise ValueError(f'حقل استعلام ناقص: {key}')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', query['id']) or query['id'] in seen:
            raise ValueError('معرف استعلام غير صالح أو مكرر')
        seen.add(query['id'])
        count_matches([], query.get('terms'), surah=query.get('surah'), include_opening_basmalas=query.get('include_opening_basmalas', False))
        if 'expected_count' in query and (type(query['expected_count']) is not int or query['expected_count'] < 0):
            raise ValueError('العدد المتوقع يجب أن يكون عددا صحيحا غير سالب')


def validate_query_links(records, query_ids):
    for record in records:
        links = record.get('query_ids', [])
        if not isinstance(links, list) or any(not isinstance(link, str) for link in links):
            raise ValueError('إحالات الاستعلامات يجب أن تكون قائمة معرفات')
        if len(links) != len(set(links)) or not set(links) <= query_ids:
            raise ValueError('إحالة استعلام مفقودة أو مكررة')
        if record['category'] == 'counts' and not links:
            raise ValueError('الدليل العددي يحتاج استعلاما قابلا للإعادة')


def validate_annotations(annotation, verses, sha256, registered_queries=None):
    """تحقق من اكتمال الوقوع تحت القوائم المعلنة؛ لا يحكم على تصنيف المعنى."""
    if annotation.get('corpus') != 'simple-clean' or annotation.get('corpus_sha256') != sha256:
        raise ValueError('مصدر التعليقات لا يطابق النص المثبت')
    include_basmalas = annotation.get('include_opening_basmalas')
    if type(include_basmalas) is not bool:
        raise ValueError('يلزم التصريح بسياسة البسملة في التعليقات')
    queries = annotation.get('queries')
    validate_queries(queries)
    if not queries:
        raise ValueError('ملف التعليقات بلا قوائم ألفاظ')
    registry = {query['id']: query for query in registered_queries} if registered_queries is not None else None
    expected = set()
    for query in queries:
        terms = query['terms']
        if len(terms) != len(set(terms)) or any(term.split() != [term] for term in terms):
            raise ValueError('قوائم التعليقات تحتاج كلمات مفردة غير مكررة')
        if 'include_opening_basmalas' in query and query['include_opening_basmalas'] != include_basmalas:
            raise ValueError('سياسة البسملة متعارضة داخل ملف التعليقات')
        if registry is not None:
            registered = registry.get(query['id'])
            if registered is None or set(registered['terms']) != set(terms) or registered.get('surah') != query.get('surah') or registered.get('include_opening_basmalas', False) != include_basmalas:
                raise ValueError(f'قائمة التعليقات تختلف عن الاستعلام المسجل: {query["id"]}')
        result = count_matches(verses, terms, include_opening_basmalas=include_basmalas, surah=query.get('surah'))
        for match in result['matches']:
            expected.update((query['id'], match['ref'], position, match['term']) for position in match['token_positions'])
    occurrences = annotation.get('occurrences')
    if not isinstance(occurrences, list):
        raise ValueError('يلزم جدول وقوع في ملف التعليقات')
    actual = set()
    for row in occurrences:
        if not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key] for key in ['query_id', 'verse_ref', 'source_token']):
            raise ValueError('بيانات وقوع ناقصة')
        if type(row.get('source_word_position')) is not int or row['source_word_position'] < 1:
            raise ValueError('موقع الكلمة يجب أن يكون عددا صحيحا يبدأ من 1')
        key = (row['query_id'], row['verse_ref'], row['source_word_position'], row['source_token'])
        if key in actual:
            raise ValueError(f'وقوع مكرر في التعليقات: {key}')
        actual.add(key)
    if actual != expected:
        raise ValueError(f'التعليقات لا تغطي القوائم المعلنة: ناقص {len(expected - actual)}، زائد أو مختلف {len(actual - expected)}')


def universe_results(verses, groups):
    queries = []
    for group in groups:
        for field in ['semantic_caveats_ar', 'excluded_candidate_forms']:
            if not isinstance(group.get(field), list) or any(not isinstance(v, str) for v in group[field]):
                raise ValueError(f'قائمة معجم الكون غير صالحة: {field}')
        queries.append({key: group.get(key) for key in ['id', 'title_ar', 'terms', 'scope_note_ar']})
    validate_queries(queries)
    results = []
    for group in groups:
        result = concordance(verses, group['terms'], radius=1)
        result.update({key: group[key] for key in ['id', 'title_ar', 'scope_note_ar', 'semantic_caveats_ar', 'excluded_candidate_forms']})
        result['forms'] = [{'form': term, 'count': count_matches(verses, [term])['count']} for term in group['terms']]
        results.append(result)
    return results


def validate_reading(ledger, verses, sha256):
    if ledger.get('completed') is not True or ledger.get('method') != 'model_visible_complete_text':
        raise ValueError('لا تعتمد قراءة غير مكتملة أو قراءة برمجية فقط')
    if ledger.get('corpus_sha256') != sha256 or not ledger.get('reader_id') or not ledger.get('compaction_note_ar'):
        raise ValueError('بيانات مصدر القراءة أو حدود السياق ناقصة')
    refs = [v.ref for v in verses]
    indices = {ref: i for i, ref in enumerate(refs)}
    next_index = 0
    for block in ledger.get('blocks', []):
        start = indices.get(block.get('start_ref'))
        end = indices.get(block.get('end_ref'))
        if start is None or end is None or start != next_index or end < start:
            raise ValueError('فجوة أو تكرار أو مرجع غير صالح في سجل القراءة')
        if block.get('verse_count') != end - start + 1 or not block.get('notes_ar'):
            raise ValueError('عدد آيات المقطع أو ملاحظته غير صالح')
        next_index = end + 1
    if next_index != len(refs):
        raise ValueError('سجل القراءة لا يغطي القرآن كاملا')


def validate_record(record, verses, completed_readers):
    for field in ['id', 'title_ar', 'claim_ar', 'observation_ar', 'interpretation_ar']:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f'حقل دليل ناقص: {field}')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', record['id']):
        raise ValueError('معرف دليل غير صالح')
    if record.get('status') not in STATUSES or record.get('category') not in CATEGORIES:
        raise ValueError('تصنيف الدليل أو حالته غير معروفة')
    if record.get('novelty') not in {'previously_published', 'not_assessed', 'no_prior_found_in_documented_search'}:
        raise ValueError('وصف الجدة غير صالح')
    for field in ['limitations_ar', 'next_questions_ar', 'verse_refs', 'reviewed_by']:
        if not isinstance(record.get(field), list) or not record[field] or any(not isinstance(v, str) or not v.strip() for v in record[field]):
            raise ValueError(f'قائمة مطلوبة غير صالحة: {field}')
    valid_refs = {v.ref for v in verses}
    if not set(record['verse_refs']) <= valid_refs:
        raise ValueError('الدليل يشير إلى آية غير موجودة')
    if not set(record['reviewed_by']) <= completed_readers:
        raise ValueError('الدليل يعتمد على باحث لم يكمل القراءة')
    if not isinstance(record.get('baseline_ids'), list):
        raise ValueError('يلزم تحديد الدراسات التي تنطلق منها الفرضية')
    if not isinstance(record.get('sources'), list) or not record['sources']:
        raise ValueError('لا دليل دون مصادر')
    for source in record['sources']:
        if any(not isinstance(source.get(f), str) or not source[f].strip() for f in ['id','title','url','kind','locator','supports_ar','accessed_at']):
            raise ValueError('توثيق مصدر ناقص')
        url = urlparse(source['url'])
        if url.scheme not in {'http', 'https'} or not url.netloc:
            raise ValueError('رابط مصدر غير صالح')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['accessed_at']):
            raise ValueError('تاريخ توثيق غير صالح')


def build_catalog(root):
    root = Path(root)
    verses = load_corpus(root)
    manifest = verify_sources(root)
    sha256 = manifest['files'][CORPORA['simple-clean']]['sha256']
    readers = []
    for path in sorted((root / 'research/readings').glob('*.json')):
        ledger = json.loads(path.read_text())
        validate_reading(ledger, verses, sha256)
        if ledger['reader_id'] in {r['reader_id'] for r in readers}:
            raise ValueError('معرف باحث مكرر')
        readers.append(ledger)
    records = []
    for path in sorted((root / 'research/records').glob('*.json')):
        record = json.loads(path.read_text())
        validate_record(record, verses, {r['reader_id'] for r in readers})
        if path.stem != record['id'] or record['id'] in {r['id'] for r in records}:
            raise ValueError('معرف الدليل مكرر أو مختلف عن اسم ملفه')
        records.append(record)
    all_ids = {r['id'] for r in records}
    for record in records:
        if not set(record['baseline_ids']) <= all_ids or record['id'] in record['baseline_ids']:
            raise ValueError('إحالة أساس بحثي غير صالحة')
    queries = json.loads((root / 'research/queries.json').read_text())
    validate_queries(queries)
    validate_query_links(records, {q['id'] for q in queries})
    annotation_summaries = []
    for path in sorted((root / 'research/annotations').glob('*.json')):
        annotation = json.loads(path.read_text())
        try:
            validate_annotations(annotation, verses, sha256, queries)
        except ValueError as error:
            raise ValueError(f'{path.name}: {error}') from error
        if annotation.get('reader_id') not in {r['reader_id'] for r in readers}:
            raise ValueError('التعليقات تعتمد على باحث لم يكمل القراءة')
        if annotation.get('source_notice') != (root / 'data/SOURCE-LICENSE.txt').read_text():
            raise ValueError(f'إشعار المصدر ناقص في {path.name}')
        annotation_summaries.append({
            'file': f'research/annotations/{path.name}',
            'query_ids': [q['id'] for q in annotation['queries']],
            'occurrence_rows': len(annotation['occurrences']),
            'notice_ar': 'تم التحقق من اكتمال المطابقة ومواقع الكلمات تحت القوائم المعلنة؛ تصنيفات المعنى تحتاج مراجعة مستقلة.',
        })
    results = []
    ids = set()
    for query in queries:
        if query['id'] in ids:
            raise ValueError('معرف استعلام مكرر')
        ids.add(query['id'])
        result = concordance(verses, query['terms'], radius=1, surah=query.get('surah'), include_opening_basmalas=query.get('include_opening_basmalas', False))
        result.update({'id': query['id'], 'title_ar': query['title_ar'], 'scope_note_ar': query['scope_note_ar']})
        if 'expected_count' in query:
            result['expected_count'] = query['expected_count']
            result['reproduced'] = result['count'] == query['expected_count']
        results.append(result)
    return {
        'project': 'WhyQaraan', 'schema_version': 1,
        'source': manifest, 'source_notice': (root / 'data/SOURCE-LICENSE.txt').read_text(),
        'reading_notice_ar': 'سجلات القراءة إقرارات من الباحثين مع تغطية قابلة للتحقق؛ لا تثبت الفهم أو تمنع ضغط السياق، ولا يغني فحصها البرمجي عن مراجعة النص والمصادر.',
        'readers': readers, 'records': records, 'queries': results,
        'annotations': annotation_summaries,
    }
