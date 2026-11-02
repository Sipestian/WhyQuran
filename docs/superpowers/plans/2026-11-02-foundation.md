# WhyQaraan Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** تأسيس بحث عربي قابل للتدقيق مع نص كامل وأدوات عد وفهرسة ومقالات مستقبلية.

**Architecture:** ملفات المصدر ثابتة ومثبتة بالبصمة؛ أدوات Python بلا اعتماديات خارجية؛ أدلة ونتائج JSON ومقالات Markdown قابلة للاستهلاك بواسطة Astro ثابت لاحقا.

**Tech Stack:** Python 3.11+ standard library, JSON, Markdown; Astro static للمرحلة اللاحقة.

**Spec:** `docs/superpowers/specs/2026-11-02-foundation.md`

## Global Constraints

- العربية لغة البحث والمقالات.
- جميع ملفات المصدر محفوظة بلا تعديل مع الرخصة والبصمة.
- كل وكيل بحثي يقرأ القرآن كاملا قبل اعتماد دراساته.
- لا تُعرض الفرضية بوصفها حقيقة أو معجزة مثبتة.
- لا خادم تطبيق دائم لخدمة المقالات المستقبلية.

## Review Focus

- البسملة الافتتاحية قد تضخم العد؛ اختبار الفاتحة والتوبة والنمل وأول سورة أخرى.
- نص ناقص أو مبدل أو معرفات مكررة؛ رفضه قبل الحساب.
- مطابقة جزء كلمة أو جمع أشكال مكررة؛ منع تضخم النتيجة.
- سجل قراءة ناقص أو مكرر؛ منع اعتماده في تصدير الأدلة.
- تفسير جازم أو رابط لا يسند الدعوى؛ مراجعة بشرية/بحثية للمصدر والحدود، لا تكفي صحة JSON.

### Task 1: سلامة النص والعد والسياق

**Files:** `quran_research/corpus.py`, `quran_research/__main__.py`, `tests/test_corpus.py`, `data/manifest.json`.
**Interfaces:** `parse_text(text) -> list[Verse]`; `load_corpus(root, corpus='simple-clean') -> list[Verse]`; `count_matches(verses, terms, include_opening_basmalas=False, surah=None) -> dict`; `concordance(verses, terms, radius=1, **options) -> dict`.

- [x] اكتب اختبارات بمدخلات مستقلة صغيرة: يوم لا يطابق يومئذ؛ العبارات لا تتجاوز الآيات؛ تكرار عبارة داخل الآية يحتسب؛ قواعد البسملة؛ رفض الفجوات والمعرفات المكررة.
- [x] شغّل الاختبارات قبل التنفيذ وتحقق من الفشل لغياب الوظيفة.
- [x] نفذ التحميل المثبت بالبصمة والتحقق من جميع المعرفات ببيانات تنزيل، ثم العد والسياق وCLI.
- [x] شغّل الاختبارات والتحقق على المصدر الكامل.

### Task 2: سجلات الأدلة والقراءة والتصدير

**Files:** `quran_research/catalog.py`, `tests/test_catalog.py`, `research/records/`, `research/readings/`, `research/queries.json`, `reports/`.
**Interfaces:** `validate_reading(ledger, verses, sha256) -> None`; `build_catalog(root) -> dict`؛ المستهلك موقع ثابت لاحقا.

- [x] اكتب اختبارات رفض القراءة الناقصة أو المكررة ومراجع آيات غير موجودة وسجل بلا مصادر.
- [x] تحقق من فشل الاختبارات ثم نفذ التحقق والتصدير الحتمي.
- [x] اجمع نتائج الباحثين بعد اكتمال قراءتهم، وراجع المصادر والأوصاف العربية.
- [x] صدّر نتائج الاستعلامات ومواقعها وبيانات الأدلة دون إعادة صياغة النص المصدر.

### Task 3: المقالات والفرضيات والتسليم

**Files:** `README.md`, `docs/methodology.md`, `docs/website.md`, `research/hypotheses.json`, `content/articles/`, `research/PROGRESS.md`.

- [x] وثّق طريقة إعادة الحساب والمصادر والحدود والأسئلة المفتوحة وقاعدة تسجيل الفرضيات قبل الاختبار.
- [x] جهز مقالات عربية مسودة مرتبطة بسجلات الأدلة، مع فصل الاقتباس والتفسير والنتيجة العلمية.
- [x] اطلب مراجعة من باحث أكمل القراءة، ثم أصلح الأخطاء المهمة وأعد الاختبارات والتصدير.
- [x] احفظ commit تأسيسي محلي وقدم المسار والنتائج وحدود الإنجاز.

## توسعة أثناء التنفيذ

طلب المستخدم عد الحروف والكلمات المتكررة وألفاظ الكون. أضيفت أوامر inventory وcharacters وuniverse مع اختبارات للتطبيع الضمني، وسياسة البسملة، والمجموعات المعجمية الصريحة. عد الحروف هنا لنقاط Unicode، لا ادعاء توحيد قواعد الرسم.
