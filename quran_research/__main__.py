import argparse
import json
from pathlib import Path
import sys

from .corpus import CORPORA, load_corpus, verify_sources, count_matches, concordance, word_inventory, character_inventory
from .catalog import build_catalog, universe_results


ROOT = Path(__file__).resolve().parents[1]


def source_notice(corpus='simple-clean'):
    text = (ROOT / 'data/source' / CORPORA[corpus]).read_text()
    return 'Tanzil — https://tanzil.net\n\n' + text[text.index('# PLEASE'):]


def main():
    parser = argparse.ArgumentParser(description='WhyQaraan — فهرسة النص العربي والتحقق من الأدلة')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('verify', help='التحقق من المصدرين وجميع مراجع الآيات')
    subs.add_parser('build', help='التحقق من سجلات الأدلة والقراءة وتصدير JSON')
    subs.add_parser('inventory', help='فهرس كامل للصيغ المكتوبة ومواقعها')
    subs.add_parser('universe', help='ألفاظ الكون بقوائم الصيغ والسياقات والتحفظات الدلالية')
    chars = subs.add_parser('characters', help='تكرار نقاط Unicode والحروف والعلامات في النص')
    chars.add_argument('--corpus', choices=list(CORPORA), default='simple-clean')
    chars.add_argument('--include-opening-basmalas', action='store_true')
    for name in ['count', 'concordance', 'compare']:
        sub = subs.add_parser(name)
        sub.add_argument('terms', nargs='+', help='ألفاظ أو عبارات حرفية؛ ضع العبارة بين علامتي اقتباس')
        sub.add_argument('--corpus', choices=list(CORPORA), default='simple-clean')
        sub.add_argument('--surah', type=int)
        sub.add_argument('--include-opening-basmalas', action='store_true')
        if name == 'concordance':
            sub.add_argument('--radius', type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == 'verify':
            result = {'project': 'WhyQaraan', 'verified': True, 'corpora': {c: len(load_corpus(ROOT, c)) for c in CORPORA}, 'surahs': 114}
        elif args.command == 'universe':
            groups = json.loads((ROOT / 'research/universe-terms.json').read_text())
            groups = universe_results(load_corpus(ROOT), groups)
            report = {'corpus': 'simple-clean', 'source_sha256': verify_sources(ROOT)['files'][CORPORA['simple-clean']]['sha256'], 'source_url': 'https://tanzil.net', 'source_notice': source_notice(), 'groups': groups}
            target = ROOT / 'reports/universe.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            result = {'output': str(target), 'groups': [{'id': g['id'], 'count': g['count'], 'terms': g['terms']} for g in groups]}
        elif args.command == 'characters':
            index = character_inventory(load_corpus(ROOT, args.corpus), args.include_opening_basmalas)
            index.update({'corpus': args.corpus, 'source_sha256': verify_sources(ROOT)['files'][CORPORA[args.corpus]]['sha256'], 'source_url': 'https://tanzil.net', 'source_notice': source_notice(args.corpus)})
            suffix = '-with-openings' if args.include_opening_basmalas else ''
            target = ROOT / f'reports/characters-{args.corpus}{suffix}.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
            result = {'output': str(target), **{key: index[key] for key in ['non_whitespace_codepoints', 'letter_codepoints_excluding_tatweel', 'mark_codepoints', 'tatweel_codepoints']}, 'top_characters': index['characters'][:10]}
        elif args.command == 'inventory':
            words = word_inventory(load_corpus(ROOT))
            index = {'corpus': 'simple-clean', 'source_sha256': verify_sources(ROOT)['files'][CORPORA['simple-clean']]['sha256'], 'source_url': 'https://tanzil.net', 'include_opening_basmalas': False, 'source_notice': source_notice(), 'words': words}
            target = ROOT / 'reports/word-index.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')) + '\n')
            result = {'output': str(target), 'written_forms': len(words), 'tokens': sum(w['count'] for w in words), 'forms_occurring_once': sum(w['count'] == 1 for w in words), 'forms_repeated': sum(w['count'] > 1 for w in words), 'top_forms': [{'word': w['word'], 'count': w['count']} for w in sorted(words, key=lambda w: (-w['count'], w['word']))[:30]]}
            summary = {**result, 'output': 'reports/word-index.json', 'corpus': 'simple-clean', 'source_sha256': index['source_sha256'], 'include_opening_basmalas': False, 'method_ar': 'الصيغ المكتوبة المفصولة بالمسافات دون جمع اللواصق أو التفريق الدلالي بين الألفاظ المشتركة في الرسم؛ المصدر الكامل المثبت. ليست أعداد الجذور أو المفردات المعجمية.', 'source_notice': source_notice()}
            (ROOT / 'reports/repetition-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
        elif args.command == 'build':
            catalog = build_catalog(ROOT)
            target = ROOT / 'reports/catalog.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
            result = {'output': str(target), 'records': len(catalog['records']), 'readers': len(catalog['readers']), 'queries': [{'id': q['id'], 'count': q['count'], 'reproduced': q.get('reproduced')} for q in catalog['queries']]}
        else:
            verses = load_corpus(ROOT, args.corpus)
            options = {'surah': args.surah, 'include_opening_basmalas': args.include_opening_basmalas}
            if args.command == 'compare':
                result = {'comparisons': [count_matches(verses, [term], **options) for term in dict.fromkeys(args.terms)]}
            elif args.command == 'concordance':
                result = concordance(verses, args.terms, radius=args.radius, **options)
            else:
                result = count_matches(verses, args.terms, **options)
            result['corpus'] = args.corpus
            result['source_sha256'] = verify_sources(ROOT)['files'][CORPORA[args.corpus]]['sha256']
            result['source_url'] = 'https://tanzil.net'
            result['source_notice'] = source_notice(args.corpus)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'تعذر إكمال الأمر: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
