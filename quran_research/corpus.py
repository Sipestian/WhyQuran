"""النص المرجعي، المطابقة الحرفية، وفهارس الاستعمال والسياق."""

from dataclasses import dataclass
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import unicodedata


CORPORA = {'simple-clean': 'tanzil-simple-clean.txt', 'uthmani': 'tanzil-uthmani.txt'}
BASMALAS = {
    tuple('بسم الله الرحمن الرحيم'.split()),
    tuple('بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ'.split()),
    tuple('بِّسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ'.split()),
}


@dataclass(frozen=True)
class Verse:
    surah: int
    ayah: int
    text: str

    @property
    def ref(self):
        return f'{self.surah}:{self.ayah}'


def parse_text(text):
    verses = []
    previous = (0, 0)
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) != 3 or not parts[0].isascii() or not parts[1].isascii() or not parts[0].isdigit() or not parts[1].isdigit() or not parts[2].strip():
            raise ValueError(f'سطر مصدر غير صالح: {number}')
        surah, ayah = int(parts[0]), int(parts[1])
        if not 1 <= surah <= 114 or ayah < 1 or (surah, ayah) <= previous:
            raise ValueError(f'مرجع مكرر أو خارج الترتيب: {surah}:{ayah}')
        previous = (surah, ayah)
        verses.append(Verse(surah, ayah, parts[2]))
    if not verses:
        raise ValueError('النص خال من الآيات')
    return verses


def verify_sources(root):
    root = Path(root)
    manifest = json.loads((root / 'data/manifest.json').read_text())
    for name, info in manifest['files'].items():
        data = (root / 'data/source' / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != info['sha256'] or len(data) != info['bytes']:
            raise ValueError(f'تغير ملف المصدر: {name}')
    return manifest


def load_corpus(root, corpus='simple-clean'):
    if corpus not in CORPORA:
        raise ValueError('اختر simple-clean أو uthmani')
    root = Path(root)
    verify_sources(root)
    verses = parse_text((root / 'data/source' / CORPORA[corpus]).read_text(encoding='utf-8-sig'))
    suras = ET.parse(root / 'data/source/quran-data.xml').getroot().find('suras')
    expected = [(int(s.attrib['index']), aya) for s in suras for aya in range(1, int(s.attrib['ayas']) + 1)]
    if len(suras) != 114 or len(expected) != 6236 or [(v.surah, v.ayah) for v in verses] != expected:
        raise ValueError('تغطية الآيات لا تطابق بيانات السور المرجعية')
    for verse in verses:
        if verse.ayah == 1 and verse.surah not in (1, 9) and tuple(verse.text.split()[:4]) not in BASMALAS:
            raise ValueError(f'البسملة الافتتاحية غير متوقعة: {verse.ref}')
    return verses


def _tokens(verse, include_opening_basmalas):
    tokens = verse.text.split()
    offset = 0
    if not include_opening_basmalas and verse.ayah == 1 and verse.surah not in (1, 9) and tuple(tokens[:4]) in BASMALAS:
        offset = 4
    return tokens[offset:], offset


def count_matches(verses, terms, include_opening_basmalas=False, surah=None):
    if not isinstance(terms, list) or not terms or any(not isinstance(t, str) or not t.strip() for t in terms):
        raise ValueError('يلزم لفظ أو عبارة غير فارغة')
    if type(include_opening_basmalas) is not bool:
        raise ValueError('خيار البسملة يجب أن يكون true أو false وليس نصا')
    if surah is not None and (type(surah) is not int or not 1 <= surah <= 114):
        raise ValueError('رقم السورة يجب أن يكون بين 1 و114')
    terms = list(dict.fromkeys(' '.join(t.split()) for t in terms))
    patterns = [(term, term.split()) for term in terms]
    matches = []
    count = 0
    for verse in verses:
        if surah is not None and verse.surah != surah:
            continue
        tokens, offset = _tokens(verse, include_opening_basmalas)
        for term, pattern in patterns:
            positions = [i + 1 + offset for i in range(len(tokens) - len(pattern) + 1) if tokens[i:i + len(pattern)] == pattern]
            if positions:
                count += len(positions)
                matches.append({'ref': verse.ref, 'term': term, 'token_positions': positions, 'text': verse.text})
    return {
        'terms': terms, 'count': count, 'matching_verses': len({m['ref'] for m in matches}),
        'surah': surah, 'include_opening_basmalas': include_opening_basmalas,
        'method_ar': 'مطابقة متتاليات كلمات مفصولة بمسافات؛ لا تطبيع للحروف ولا تحليل للجذور. مواقع الكلمات تبدأ من 1 في سطر المصدر الأصلي. تجمع مطابقة كل عبارة مستقلة، وقد تتداخل العبارات المختلفة.',
        'matches': matches,
    }


def concordance(verses, terms, radius=1, **options):
    if type(radius) is not int or not 0 <= radius <= 10:
        raise ValueError('نطاق السياق يجب أن يكون بين 0 و10 آيات')
    result = count_matches(verses, terms, **options)
    lookup = {(v.surah, v.ayah): v for v in verses}
    for match in result['matches']:
        surah, ayah = map(int, match['ref'].split(':'))
        match['context'] = [
            {'ref': verse.ref, 'text': verse.text}
            for n in range(max(1, ayah - radius), ayah + radius + 1)
            if (verse := lookup.get((surah, n))) is not None
        ]
    return result


def word_inventory(verses, include_opening_basmalas=False):
    """كل صيغة مكتوبة ومواقعها، دون ادعاء التحليل الصرفي أو تحديد الأسماء."""
    if type(include_opening_basmalas) is not bool:
        raise ValueError('خيار البسملة يجب أن يكون true أو false وليس نصا')
    inventory = {}
    for verse in verses:
        tokens, offset = _tokens(verse, include_opening_basmalas)
        for position, word in enumerate(tokens, offset + 1):
            entry = inventory.setdefault(word, {'word': word, 'count': 0, 'locations': []})
            entry['count'] += 1
            entry['locations'].append([verse.ref, position])
    return [inventory[word] for word in sorted(inventory)]


def character_inventory(verses, include_opening_basmalas=False):
    """عد نقاط Unicode كما هي؛ ليس تحقيقا تقليديا لعد حروف الرسم."""
    if type(include_opening_basmalas) is not bool:
        raise ValueError('خيار البسملة يجب أن يكون true أو false وليس نصا')
    counts = Counter()
    by_surah = {}
    for verse in verses:
        tokens, _ = _tokens(verse, include_opening_basmalas)
        local = Counter(''.join(tokens))
        counts.update(local)
        by_surah.setdefault(verse.surah, Counter()).update(local)

    def totals(counter):
        return {
            'non_whitespace_codepoints': sum(counter.values()),
            'letter_codepoints_excluding_tatweel': sum(n for c, n in counter.items() if unicodedata.category(c).startswith('L') and c != 'ـ'),
            'mark_codepoints': sum(n for c, n in counter.items() if unicodedata.category(c).startswith('M')),
            'tatweel_codepoints': counter.get('ـ', 0),
        }

    return {
        'method_ar': 'نقاط Unicode غير البيضاء في متن الآيات فقط؛ لا ترقيم ولا رخصة ولا تطبيع Unicode ولا دمج للهمزات. يعرض تصنيف الحرف والعلامة والتطويل منفصلا. هذا وصف لترميز الملف المحدد وليس عد الحروف التراثي أو الأصوات أو الأشكال المرئية.',
        'unicode_version': unicodedata.unidata_version,
        'include_opening_basmalas': include_opening_basmalas,
        **totals(counts),
        'characters': [{'character': c, 'codepoint': f'U+{ord(c):04X}', 'category': unicodedata.category(c), 'unicode_name': unicodedata.name(c, 'UNKNOWN'), 'count': n} for c, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))],
        'surahs': [{'surah': s, **totals(c)} for s, c in sorted(by_surah.items())],
    }
