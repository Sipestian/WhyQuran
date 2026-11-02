"""Render the readable editorial register from its authoritative JSON data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = json.loads((ROOT / "research/website-backlog.json").read_text())
CATEGORIES = {
    "wording": "الألفاظ والنظم والبلاغة",
    "counts": "الأسماء والكلمات والحروف والأعداد",
    "science": "الكون والعلم والوراثة",
    "family": "الزواج والطلاق وبناء الأحكام",
    "methodology": "منهج البحث والأسئلة المفتوحة",
}
STATUSES = {
    "idea": "سؤال مقترح",
    "research": "قيد البحث",
    "draft": "له مسودة",
    "reviewed": "اجتاز مراجعة داخلية",
}

lines = [
    "# موضوعات موقع WhyQuran",
    "",
    f"هذا سجل ما يستحق الحفظ للموقع، استجابة لطلب المالك ألا يضيع شيء من البحث. يضم **{len(TOPICS)} موضوعا** في الألفاظ والأعداد والعلم والأسرة والمنهج. الحالة والخطوة التالية تميزان الفكرة من المقال المراجع.",
    "",
    "السجل المنظم المعتمد هو [website-backlog.json](website-backlog.json)، وتعرضه صفحة «خريطة البحث» في الموقع. يولد هذا الملف بأمر `python3 tools/render_backlog.py`؛ تحدث بطاقة JSON ثم أعد التوليد، بدلا من تعديل نسختين باليد. لا تحذف النتائج السلبية أو الأسئلة غير المحسومة.",
    "",
    "## ما يستحق الظهور أولا",
    "",
    "تبدأ القراءة بطريقة عد الكلمة، ومثال تستطع/تسطع، ومعجم ألفاظ الكون، ثم القمر والتمدد والحديد والنظم بعد مراجعة كل مقال. تعرض الوراثة والأسرة بأسئلة محددة ومصادرها والخلاف المؤثر فيها. لا يوجد حتى الآن اكتشاف علمي أصلي مثبت للمشروع.",
    "",
    "## درجات المادة",
    "",
    "- **له مسودة:** مادة محررة أو يجري تحريرها؛ لا يعني اعتماد النشر.",
    "- **قيد البحث:** مصادر أو نتائج أولية تحتاج استكمال المقال والمراجعة.",
    "- **سؤال مقترح:** محفوظ للبحث؛ لا نتيجة محسوبة أو مثبتة بعد.",
    "- **اجتاز مراجعة داخلية:** راجع قارئ مستقل المقال في نطاقه المعلن؛ ليست شهادة تحكيم علمي أو اعتماد عالم بشري.",
    "",
]

for category, title in CATEGORIES.items():
    lines.extend([f"## {title}", ""])
    for topic in (t for t in TOPICS if t["category"] == category):
        lines.extend([
            f"### {topic['title_ar']}",
            "",
            f"- المعرّف: `{topic['id']}`؛ الحالة: {STATUSES[topic['status']]}.",
            f"- السؤال: {topic['question_ar']}",
            f"- الأساس الحالي: {topic['baseline_ar']}",
        ])
        if topic["verse_refs"]:
            verses = "، ".join(f"`{ref}`" for ref in topic["verse_refs"])
            lines.append(f"- مواضع الانطلاق: {verses}. ليست بديلا عن استقصاء المواضع.")
        if topic["evidence_ids"]:
            evidence = "، ".join(f"[{eid}](records/{eid}.json)" for eid in topic["evidence_ids"])
            lines.append(f"- الأدلة الحالية: {evidence}.")
        if topic["source_urls"]:
            sources = "، ".join(f"[المصدر {i}]({url})" for i, url in enumerate(topic["source_urls"], 1))
            lines.append(f"- المصادر المفتوحة: {sources}.")
        slug = topic.get("article_slug")
        if slug and (ROOT / f"content/articles/{slug}.md").is_file():
            lines.append(f"- المقال: [{slug}](../content/articles/{slug}.md).")
        lines.extend([
            f"- الخطوة التالية: {topic['next_step_ar']}",
            f"- القيد الذي يجب ألا يضيع: {topic['qualification_ar']}",
            "",
        ])

lines.extend([
    "## ملفات المتابعة",
    "",
    "- [الفرضيات وقواعد اختبارها](hypotheses.json).",
    "- [تقدم العمل والتحقق](PROGRESS.md).",
    "- [مذكرة الألفاظ](notes/wording.md)، [مذكرة العلم](notes/science.md)، [مذكرة الأسرة](notes/family-law.md).",
])
for name, label in [("wording-website-backlog", "تفاصيل موضوعات الألفاظ"), ("science-website-backlog", "تفاصيل موضوعات العلم")]:
    if (ROOT / f"research/notes/{name}.md").exists():
        lines.append(f"- [{label}](notes/{name}.md).")
lines.extend([
    "",
    "## ما يلزم في بطاقة المقال",
    "",
    "السؤال المحدد، نص الآيات وسياقها، المصدر السابق، الملاحظة المعاد فحصها، التفسير المنسوب، الدليل العلمي وتاريخه عند الحاجة، الاعتراضات، النتيجة وحدودها، وقاعدة إعادة الحساب. تحفظ الجدة بوصفها غير مفحوصة حتى بحث السوابق، وتحفظ الفرضية بوصفها فرضية حتى الاختبار. المصدر العلمي يثبت ما يقوله فعلا، ولا يجعل تفسيرنا للآية حقيقة تجريبية.",
    "",
])
(ROOT / "research/WEBSITE-BACKLOG.md").write_text("\n".join(lines))
print(f"Rendered {len(TOPICS)} topics to research/WEBSITE-BACKLOG.md")
