"""Registry of the grammatical rules the engine implements.

Rules are data, separate from the code that applies them, so explanations,
references and review status can later move into the knowledge base without
touching the generator. Every rule here is a Phase 1 seed: implemented and
tested, but not yet signed off by a qualified language specialist.
"""

from __future__ import annotations

from dataclasses import dataclass

GHALAYINI = "al-Ghalayini, Jamiʿ al-Durus al-ʿArabiyya — al-muthanna (تثنية المقصور والممدود والمنقوص)"
HAMZA_ORTHOGRAPHY = "Standard Arabic orthography of medial hamza (قواعد كتابة الهمزة المتوسطة); citation to be confirmed"
ORTHOGRAPHY = "Standard Arabic orthography (قواعد الإملاء); citation to be confirmed"
GHALAYINI_DECL = "al-Ghalayini, Jamiʿ al-Durus al-ʿArabiyya — iʿrab al-ism, al-mamnuʿ min al-sarf"
GHALAYINI_PLURAL = "al-Ghalayini, Jamiʿ al-Durus al-ʿArabiyya — al-jamʿ (المذكر السالم، المؤنث السالم، التكسير)"


@dataclass(frozen=True)
class Rule:
    id: str
    name_ar: str
    explanation_ar: str
    explanation_en: str
    example: str
    reference: str
    confidence: float          # reliability of the rule itself when its conditions hold
    review_status: str = "pending_specialist_review"

    def explanation(self, lang: str = "en") -> str:
        return self.explanation_ar if lang == "ar" else self.explanation_en

    def to_dict(self) -> dict:
        return dict(self.__dict__)


_RULES = [
    Rule(
        "dual.sound", "تثنية الاسم الصحيح الآخر",
        "يُثنّى الاسم بزيادة ألف ونون مكسورة في الرفع، وياء ساكنة مفتوح ما قبلها ونون مكسورة في النصب والجر.",
        "The dual adds -āni (ـانِ) in the nominative and -ayni (ـَيْنِ) in the accusative and genitive.",
        "كتاب ← كتابانِ / كتابَيْنِ", GHALAYINI, 0.97,
    ),
    Rule(
        "dual.teh_marbuta", "التاء المربوطة في التثنية",
        "تُكتب التاء المربوطة تاءً مفتوحة عند إلحاق علامة التثنية.",
        "Ta marbuta (ة) is written as an open ta (ت) before the dual suffix.",
        "شجرة ← شجرتانِ / شجرتَيْنِ", GHALAYINI, 0.97,
    ),
    Rule(
        "dual.construct_nun_drop", "حذف نون المثنى للإضافة",
        "تُحذف نون المثنى إذا أُضيف: كتابا الطالبِ، كتابَيِ الطالبِ.",
        "The final nun of the dual is dropped in the construct state (iḍāfa).",
        "كتابانِ ← كتابا الطالبِ", GHALAYINI, 0.97,
    ),
    Rule(
        "dual.maqsur.over_three", "تثنية المقصور الزائد على ثلاثة",
        "إذا كانت ألف المقصور رابعة فصاعدًا قُلبت ياءً.",
        "When the alif of a maqsur noun is the fourth letter or later, it becomes yeh.",
        "مستشفى ← مستشفيانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.maqsur.trilateral_waw", "تثنية المقصور الثلاثي أصل ألفه واو",
        "إذا كانت ألف المقصور ثالثة منقلبة عن واو رُدّت إلى الواو.",
        "A third-letter alif derived from waw reverts to waw.",
        "عصا ← عصوانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.maqsur.trilateral_yeh", "تثنية المقصور الثلاثي أصل ألفه ياء",
        "إذا كانت ألف المقصور ثالثة منقلبة عن ياء قُلبت ياءً.",
        "A third-letter alif derived from yeh becomes yeh.",
        "فتى ← فتيانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.manqus", "تثنية المنقوص",
        "تثبت ياء المنقوص عند التثنية، وتُردّ إن كانت محذوفة.",
        "The final yeh of a manqus noun is kept, and restored if it had been dropped.",
        "القاضي ← القاضيانِ؛ قاضٍ ← قاضيانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.mamdud.original", "تثنية الممدود همزته أصلية",
        "تبقى الهمزة الأصلية على حالها.",
        "An original (root) hamza is kept unchanged.",
        "إنشاء ← إنشاءانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.mamdud.feminine", "تثنية الممدود همزته للتأنيث",
        "تُقلب همزة التأنيث واوًا.",
        "A feminine-marker hamza becomes waw.",
        "صحراء ← صحراوانِ", GHALAYINI, 0.95,
    ),
    Rule(
        "dual.mamdud.substituted", "تثنية الممدود همزته منقلبة",
        "يجوز في الهمزة المنقلبة عن واو أو ياء إبقاؤها وقلبها واوًا.",
        "A hamza substituted for waw/yeh may be kept or changed to waw; both are valid.",
        "سماء ← سماءانِ / سماوانِ", GHALAYINI, 0.9,
    ),
    Rule(
        "dual.mamdud.ilhaq", "تثنية الممدود همزته للإلحاق",
        "يجوز في همزة الإلحاق إبقاؤها وقلبها واوًا.",
        "An ilḥāq hamza may be kept or changed to waw; both are valid.",
        "علباء ← علباوانِ / علباءانِ", GHALAYINI, 0.9,
    ),
    Rule(
        "dual.hamza.alif_seat", "الهمزة على الألف قبل ألف التثنية",
        "إذا كانت الهمزة على ألف ولحقتها ألف التثنية كُتبتا مدّة (آ)، وتبقى على الألف قبل الياء.",
        "A final hamza on alif merges with the dual alif into madda (آ); before yeh it stays on alif.",
        "مبدأ ← مبدآنِ / مبدأَيْنِ", HAMZA_ORTHOGRAPHY, 0.9,
    ),
    Rule(
        "dual.hamza.after_yeh", "الهمزة بعد ياء ساكنة",
        "تُكتب الهمزة على نبرة (ئ) إذا سبقتها ياء ساكنة وصارت متوسطة.",
        "A hamza after a quiescent yeh is written on a yeh-seat (ئ) once it becomes medial.",
        "شيء ← شيئانِ / شيئَيْنِ", HAMZA_ORTHOGRAPHY, 0.9,
    ),
    Rule(
        "dual.hamza.after_waw", "الهمزة بعد واو ساكنة",
        "تُكتب الهمزة المفتوحة بعد واو ساكنة مفردة على السطر.",
        "A hamza with fatha after a quiescent waw stays on the line (ء).",
        "ضوء ← ضوءانِ / ضوءَيْنِ", HAMZA_ORTHOGRAPHY, 0.85,
    ),
    Rule(
        "dual.hamza.after_sakin_consonant", "الهمزة بعد حرف صحيح ساكن",
        "تُكتب الهمزة المفتوحة بعد ساكن صحيح على السطر قبل ألف التثنية، وعلى الألف قبل الياء.",
        "After a quiescent consonant, the hamza stays on the line before the dual alif, and sits on alif before yeh.",
        "جزء ← جزءانِ / جزأَيْنِ", HAMZA_ORTHOGRAPHY, 0.85,
    ),
    Rule(
        "dual.hamza.seat_kept", "بقاء كرسي الهمزة",
        "تبقى الهمزة على كرسيّها (ئ / ؤ) لأن حركة ما قبلها هي الأقوى.",
        "A hamza already on ئ or ؤ keeps its seat, governed by the preceding vowel.",
        "شاطئ ← شاطئانِ؛ لؤلؤ ← لؤلؤانِ", HAMZA_ORTHOGRAPHY, 0.9,
    ),

    # --- Declension with short vowels ---------------------------------------
    Rule(
        "decl.triptote", "إعراب الاسم المنصرف",
        "يُرفع الاسم المنصرف بالضمة ويُنصب بالفتحة ويُجر بالكسرة، ويُنوَّن إذا لم يكن معرّفًا بأل ولا مضافًا.",
        "A fully declinable noun takes -u / -a / -i, with tanween when it has neither ال nor a following genitive.",
        "كتابٌ، كتابًا، كتابٍ", GHALAYINI_DECL, 0.97,
    ),
    Rule(
        "decl.tanween_alif", "ألف تنوين النصب",
        "يُكتب تنوين النصب بألف بعد الحرف الأخير.",
        "Accusative tanween is written with an alif after the last letter.",
        "كتابًا", ORTHOGRAPHY, 0.97,
    ),
    Rule(
        "decl.tanween_alif_omitted", "حذف ألف تنوين النصب",
        "لا تُزاد ألف تنوين النصب بعد التاء المربوطة، ولا بعد الهمزة المسبوقة بألف، ولا بعد الهمزة على الألف.",
        "No extra alif is written after ة, after hamza preceded by alif, or after hamza on alif.",
        "شجرةً، سماءً، خطأً", ORTHOGRAPHY, 0.95,
    ),
    Rule(
        "decl.diptote", "إعراب الممنوع من الصرف",
        "لا يُنوَّن الممنوع من الصرف، ويُجرّ بالفتحة نيابةً عن الكسرة.",
        "A diptote takes no tanween, and its genitive takes fatha in place of kasra.",
        "مررتُ بمدارسَ كثيرةٍ", GHALAYINI_DECL, 0.95,
    ),
    Rule(
        "decl.diptote_kasra_when_definite", "جرّ الممنوع من الصرف بالكسرة",
        "يُجرّ الممنوع من الصرف بالكسرة إذا عُرّف بأل أو أُضيف.",
        "A diptote takes kasra in the genitive when it has ال or is in the construct state.",
        "في المدارسِ", GHALAYINI_DECL, 0.95,
    ),
    Rule(
        "decl.manqus", "إعراب المنقوص",
        "تُقدَّر الضمة والكسرة على ياء المنقوص وتظهر الفتحة، وتُحذف الياء في الرفع والجر إذا نُوِّن.",
        "Nominative and genitive are implicit on the yeh of a manqus noun and accusative fatha is visible; "
        "with tanween the yeh drops in the nominative and genitive.",
        "قاضٍ، قاضيًا، القاضي", GHALAYINI_DECL, 0.95,
    ),
    Rule(
        "decl.manqus_diptote", "إعراب المنقوص الممنوع من الصرف",
        "تُحذف ياؤه في الرفع والجر ويُعوَّض عنها بالتنوين، وتظهر الفتحة في النصب بلا تنوين.",
        "A diptote manqus drops its yeh in nominative/genitive with compensatory tanween, "
        "and takes fatha without tanween in the accusative.",
        "ليالٍ، لياليَ، الليالي", GHALAYINI_DECL, 0.9,
    ),
    Rule(
        "decl.maqsur", "إعراب المقصور",
        "تُقدَّر الحركات كلها على ألف المقصور، ويُنوَّن المنصرف منه تنوينًا ظاهرًا على ما قبل الألف.",
        "All case vowels are implicit on the maqsur alif; a declinable one shows tanween on the letter before the alif.",
        "فتًى، الفتى", GHALAYINI_DECL, 0.95,
    ),

    # --- Plurals --------------------------------------------------------------
    Rule(
        "plural.broken.lexicon", "جمع التكسير من المعجم",
        "جمع التكسير سماعيّ في أكثره، فيُؤخذ من المعجم ولا يُولَّد من وزن المفرد.",
        "Broken plurals are largely lexical, so they are taken from the lexicon, never derived from the singular's pattern.",
        "كتاب ← كُتُب؛ مدرسة ← مدارس", GHALAYINI_PLURAL, 0.9,
    ),
    Rule(
        "plural.fem.sound", "جمع المؤنث السالم",
        "يُجمع بزيادة ألف وتاء، ويُرفع بالضمة ويُنصب ويُجرّ بالكسرة، وتعامل أواخره معاملتها في التثنية.",
        "Adds ـات; nominative -u, accusative and genitive -i; final maqsur/mamdud/manqus letters change as in the dual.",
        "مستشفى ← مستشفيات؛ صحراء ← صحراوات", GHALAYINI_PLURAL, 0.95,
    ),
    Rule(
        "plural.fem.teh_marbuta_dropped", "حذف التاء المربوطة",
        "تُحذف التاء المربوطة عند الجمع بالألف والتاء.",
        "Ta marbuta is dropped before ـات.",
        "شجرة ← شجرات", GHALAYINI_PLURAL, 0.97,
    ),
    Rule(
        "plural.fem.accusative_kasra", "نصب جمع المؤنث السالم بالكسرة",
        "يُنصب جمع المؤنث السالم بالكسرة نيابةً عن الفتحة.",
        "The sound feminine plural takes kasra, not fatha, in the accusative.",
        "رأيتُ المعلماتِ", GHALAYINI_PLURAL, 0.97,
    ),
    Rule(
        "plural.fem.alif_before_teh", "الألف قبل التاء المحذوفة",
        "إذا حُذفت التاء وقبلها ألف عوملت الألف معاملة ألف المقصور: تُردّ إلى أصلها إن كانت ثالثة، وتُقلب ياءً إن زادت.",
        "When ة follows an alif, the alif is treated like a maqsur alif: third-letter alifs revert to their origin, longer ones become yeh.",
        "صلاة ← صلوات؛ فتاة ← فتيات؛ مباراة ← مباريات", GHALAYINI_PLURAL, 0.9,
    ),
    Rule(
        "plural.fem.hamza_madda", "الهمزة على الألف قبل ألف الجمع",
        "إذا وليت ألفُ الجمع همزةً على ألف كُتبتا مدّة.",
        "A hamza on alif followed by the plural alif is written as madda (آ).",
        "منشأة ← منشآت", HAMZA_ORTHOGRAPHY, 0.9,
    ),
    Rule(
        "plural.fem.itbaa", "إتباع العين للفاء في فَعْلة",
        "الاسم الثلاثي على فَعْلة صحيح العين غير مضعّفها تُفتح عينه في الجمع.",
        "In a فَعْلة noun with a sound, non-doubled middle letter, the middle letter takes fatha in the plural.",
        "سَجْدة ← سَجَدات", GHALAYINI_PLURAL, 0.9,
    ),
    Rule(
        "plural.masc.sound", "جمع المذكر السالم",
        "يُجمع بزيادة واو ونون مفتوحة رفعًا، وياء ونون مفتوحة نصبًا وجرًّا.",
        "Adds -ūna (ـونَ) in the nominative and -īna (ـينَ) in the accusative and genitive.",
        "مهندس ← مهندسون / مهندسين", GHALAYINI_PLURAL, 0.97,
    ),
    Rule(
        "plural.masc.maqsur", "جمع المقصور جمع مذكر سالمًا",
        "تُحذف ألف المقصور ويبقى ما قبلها مفتوحًا دلالةً عليها.",
        "The maqsur alif is dropped and the preceding fatha stays: -awna / -ayna.",
        "مصطفى ← مصطفَوْن / مصطفَيْن", GHALAYINI_PLURAL, 0.95,
    ),
    Rule(
        "plural.masc.manqus", "جمع المنقوص جمع مذكر سالمًا",
        "تُحذف ياء المنقوص ويُضمّ ما قبلها قبل الواو ويُكسر قبل الياء.",
        "The manqus yeh is dropped; the preceding letter takes damma before waw and kasra before yeh.",
        "محامي ← محامُون / محامِين", GHALAYINI_PLURAL, 0.95,
    ),
    Rule(
        "plural.masc.hamza_seat", "كرسي الهمزة قبل علامة الجمع",
        "تُكتب الهمزة بعد ياء ساكنة على نبرة إذا صارت متوسطة.",
        "A hamza after a quiescent yeh is written on a yeh-seat once it becomes medial.",
        "بريء ← بريئون", HAMZA_ORTHOGRAPHY, 0.85,
    ),
    Rule(
        "plural.masc.construct_nun_drop", "حذف نون جمع المذكر للإضافة",
        "تُحذف نون جمع المذكر السالم إذا أُضيف.",
        "The final nun of the sound masculine plural is dropped in the construct state.",
        "مهندسو الشركة", GHALAYINI_PLURAL, 0.97,
    ),

    # --- Context (governor immediately before the noun) -----------------------
    Rule(
        "context.preposition_genitive", "الجرّ بحرف الجرّ",
        "الاسم الواقع بعد حرف الجرّ مجرور.",
        "A noun directly after a preposition is genitive.",
        "في البيتِ؛ من المدارسِ", GHALAYINI_DECL, 0.95,
    ),
    Rule(
        "context.inna_accusative", "نصب اسم إنّ وأخواتها",
        "تنصب إنّ وأخواتها المبتدأ ويُسمّى اسمها.",
        "إنّ and its sisters make the following subject accusative.",
        "إنّ الطالبَ مجتهدٌ", GHALAYINI_DECL, 0.9,
    ),
    Rule(
        "context.kana_nominative", "رفع اسم كان وأخواتها",
        "ترفع كان وأخواتها المبتدأ ويُسمّى اسمها، وتنصب الخبر.",
        "كان and its sisters keep their subject nominative (and make the predicate accusative).",
        "كان الجوُّ جميلًا", GHALAYINI_DECL, 0.85,
    ),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}


def get_rule(rule_id: str) -> Rule:
    return RULES[rule_id]
