# ArabMorph AI

An Arabic morphology and grammar platform built around a deterministic,
framework-independent linguistic engine. Web, desktop and offline clients,
the knowledge base and the AI layer will be built on top of it in later phases.

## Status

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 — Foundation | Repo layout, engine package, normalisation, first dual rules, tests | **Done** (pending review, AM-1) |
| 2 — Linguistic engine | Declension, sound + broken plurals, exceptions, governor-based case | **Done** (pending review, AM-2) |
| 8 (early) — Desktop | Windows app (Tauri + Vue) over the offline engine, NSIS installer | **Preview** — see `desktop/` |
| 3–10 | Database, API, web frontend, documents, AI agent, sync, education, production | Not started |

## Repository layout

```
arabmorph-ai/
├── engine/                     # pure-Python morphology engine (no Django / AI imports)
│   ├── pyproject.toml
│   ├── src/arabmorph/
│   │   ├── chars.py            # Unicode constants and predicates
│   │   ├── clusters.py         # letter + diacritic clusters
│   │   ├── normalize.py        # configurable, non-destructive normalisation
│   │   ├── noun_input.py       # parse a typed noun: article, case ending, tanween
│   │   ├── classify.py         # final-letter classification → interpretations
│   │   ├── pipeline.py         # shared parse → validate → interpret → assemble
│   │   ├── orthography.py      # article (sun/moon/wasl), mark helpers
│   │   ├── declension.py       # case endings: triptote, diptote, manqus, maqsur
│   │   ├── singular.py         # declined singular forms
│   │   ├── dual.py             # dual generation
│   │   ├── plural.py           # sound masculine / sound feminine / broken plurals
│   │   ├── context.py          # case from the preceding governor
│   │   ├── generate.py         # unified generate() / paradigm()
│   │   ├── rules.py            # rule registry (AR/EN explanations, references)
│   │   ├── lexicon.py          # lexicon interface + seed loader
│   │   ├── types.py            # enums and result types
│   │   └── data/lexicon_seed.json
│   └── tests/
│       ├── corpus/             # curated corpora: dual, plural, singular, context
│       └── test_*.py
├── desktop/                    # Windows app: Tauri + Vue UI, Python stdio sidecar
├── backend/   frontend/         # created in later phases
```

`backend/` and `frontend/` do not exist yet. Like `desktop/`, they will use
`engine/` as a library.

## Windows app

The preview desktop app runs fully offline: no network, no API keys. To build
the installer, see [`desktop/README.md`](desktop/README.md).

## Setup

Requires Python 3.11+ (developed on 3.12).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e "engine[dev]"
cd engine
pytest          # tests
python -m build # sdist + wheel
```

## Usage

```bash
arabmorph dual كتاب --case accusative             # كتابَيْنِ
arabmorph dual شجرة --construct                    # شجرتا
arabmorph plural مهندس --construct                 # مُهَنْدِسُو
arabmorph plural ليلة --case accusative            # لَيَالِيَ  (diptote manqus)
arabmorph plural مدرسة                             # ambiguous: مَدَارِسُ (school) | مُدَرِّسَاتٌ (female teacher)
arabmorph plural كاتب --kind sound_masculine       # كاتبون — source "asserted", confidence capped
arabmorph singular أحمد --case genitive            # أَحْمَدَ  (diptote)
arabmorph plural مدرسة --after في --definite       # case from context: الْمَدَارِسِ / الْمُدَرِّسَاتِ
arabmorph plural صحراء --all                        # 3 cases × indefinite/definite/construct
```

```python
from arabmorph import generate, generate_in_context, Number, Case
r = generate("سماء", Number.DUAL, Case.NOMINATIVE)
[f.text for f in r.forms]   # ['سماءان', 'سماوان']  — both valid
r = generate_in_context("معلمة", Number.PLURAL, "لعلّ", definite=True)
r.forms[0].vocalized        # 'الْمُعَلِّمَاتِ' — accusative sound feminine plural takes kasra
```

Each form records the rule(s) applied, its source (`rule`, `lexicon`,
`heuristic`, `asserted`), a confidence value, the condition it depends on,
any warnings, and for plurals the plural kind and diptote status. The result
also carries assumptions and errors.

## Engine design decisions

- **Independent engine.** `arabmorph` imports only the standard library. A
  test enforces that Django, DRF, Celery, Redis and AI SDKs are never
  imported, so the same code runs in the server, the desktop app and offline.
- **Clusters, not strings.** Words are split into letter + diacritic
  clusters, so operations like "turn ة into ت" or "put fatha on the last
  letter" keep partial diacritics intact. Marks are kept in NFC canonical order.
- **Original input is preserved.** Normalisation returns the original next to
  the normalised text. Lossy options (merging alef forms, ى→ي, ة→ه) are off by
  default and flag the result as lossy.
- **Lexicon before rules.** Some facts can't be recovered from spelling: the
  origin of a maqsur alif, the type of a mamdud hamza, whether a final ي is
  manqus, whether a noun is diptote, and which plural it takes. The lexicon
  supplies them, and rules apply after.
- **Ambiguity is a result, not a guess.** When evidence is insufficient the
  engine returns `status: ambiguous` with every reading and the condition under
  which each one holds. Homographs (مَدْرَسة / مُدَرِّسة) give one reading per
  lexicon entry.
- **Rules are data.** `rules.py` holds the explanation (Arabic and English),
  example, reference and review status of each rule. In Phase 3 these move
  into the versioned knowledge base without changing the generators.

## Implemented rules

`arabmorph.RULES` is the authoritative list. Every rule is covered by at least
one case in `engine/tests/corpus/*.json`, and a test enforces this.

### Dual (Phase 1)

| Rule | Example |
| ---- | ------- |
| `dual.sound` | كتاب ← كتابانِ / كتابَيْنِ |
| `dual.teh_marbuta` | شجرة ← شجرتانِ / شجرتَيْنِ |
| `dual.construct_nun_drop` | كتابا الطالبِ / كتابَيِ الطالبِ |
| `dual.maqsur.over_three` | مستشفى ← مستشفيانِ |
| `dual.maqsur.trilateral_waw` / `_yeh` | عصا ← عصوانِ ؛ فتى ← فتيانِ |
| `dual.manqus` | القاضي ← القاضيانِ ؛ قاضٍ ← قاضيانِ |
| `dual.mamdud.original` / `feminine` | إنشاء ← إنشاءانِ ؛ صحراء ← صحراوانِ |
| `dual.mamdud.substituted` / `ilhaq` | سماء ← سماءانِ / سماوانِ (both valid) |
| `dual.hamza.*` (5 orthographic rules) | مبدأ ← مبدآن ؛ جزء ← جزءان/جزأين ؛ شيء ← شيئان |

### Declension (Phase 2)

Triptote with tanween (and the tanween alif, omitted after ة / ـاء / أ),
diptote (genitive with fatha, kasra once it has ال or is construct), manqus
(قاضٍ / قاضيًا / القاضي), diptote manqus (ليالٍ / لياليَ / الليالي), maqsur
(implicit case; فتًى).

### Plurals (Phase 2)

- **Broken plurals come only from the lexicon** (`plural.broken.lexicon`).
  They are never derived from the singular's pattern. Each records whether
  it is diptote.
- **Sound feminine** ـات: ة dropped; nominative ـاتٌ, accusative and genitive
  ـاتٍ (`plural.fem.accusative_kasra`); alif before ة treated as maqsur
  (صلوات، فتيات، مباريات); أ+ا → آ (منشآت); فَعْلة → فَعَلات for nouns only
  (سَجَدات); maqsur/mamdud/manqus endings as in the dual.
- **Sound masculine** ـون/ـين: maqsur (مصطفَوْن), manqus (محامُون), hamza seat
  (بريئون), construct drops the nun (مهندسو). Rejected for ة nouns.
- **Which plural a word takes** comes from its lexicon entry. Without an
  entry, the caller can assert a sound kind (source `asserted`, confidence
  ≤ 0.6). Otherwise ة nouns get only a conditional ـات candidate
  (confidence 0.4, status `ambiguous`), and other words get an error that
  says why.

### Context (Phase 2)

The case comes from the word directly before the noun: prepositions →
genitive, إنّ and its sisters → accusative, كان and its sisters → nominative
(stated as an assumption). Undiacritized إن/أن/كأن/لكن are refused, because
without shadda they may be different particles.

Definite (sun/moon letter, and kasra on the lam before hamzat al-waṣl),
indefinite and construct states are supported throughout.

## Known limitations (honest scope)

- **Nothing is specialist-reviewed yet.** All rules and all 41 seed lexicon
  entries are marked `pending_specialist_review` / `verified: false`. The
  orthography citations still need confirming.
- **Context is one word deep.** Only the immediately preceding governor is
  used. No sentence parsing, agreement, apposition, or verbal subjects and
  objects. The input is assumed to be a singular noun or adjective, and part
  of speech is not checked.
- **Plural coverage is lexicon-bound.** Only the seed entries have recorded
  plurals. Not covered: sound masculine plurals of mamdud nouns with
  non-original hamza and of most hamza-final words; plurals of compounds;
  the plural of a plural; the alternative vowels of فُعْلة/فِعْلة plurals
  (mentioned in a warning, not generated).
- **Words without a lexicon entry are assumed fully declinable** (not
  diptote), with a warning.
- **Not covered:** the five nouns (أب، أخ…), words with clitics (بالكتاب،
  وكتاب، كتابه), loanwords ending in ا (سينما), the dual of compound names,
  nouns that have no dual, and non-genuine iḍāfa with ال (الضاربا زيدٍ).
- **Confidence values are hand-set**, not calibrated. They rank readings;
  they are not probabilities.

## Next action

Phase 3: Django project (`backend/`) with PostgreSQL models for lexicon
entries, plurals, rules, examples, versions and reviewer decisions, mirroring
the seed JSON schema. Plus migrations, and a loader that imports
`lexicon_seed.json` as unreviewed candidates. The engine keeps its `Lexicon`
interface, and the database becomes one more source behind it.
