# ArabMorph AI — Windows desktop app

A classroom app for Arabic lessons, built with Tauri 2 + Vue 3 + TypeScript around
the offline `arabmorph` engine. The interface is in Uzbek, Arabic (RTL), Russian
and English; the language is switched in the UI and remembered on the computer.

## Sections

| Section | What it does |
| ------- | ------------ |
| **Activity** (Mashg'ulot) | Choose a direction: **Arabic → Uzbek** (the Arabic word is shown, its translation is the answer), **Uzbek → Arabic**, or **Word → answer** (the row's own answer, for grammar sets). Approved words appear one at a time, each for a set number of seconds, then the next word appears automatically. Correct / wrong buttons (keys 1 / 2) move on early; an optional pause shows the answer. A summary lists missed words and can repeat them. |
| **Test** | Questions are always worded in Uzbek: "Bu so'z o'zbekchada nima degani?" for a word with a translation, "Bu so'zning ko'pligi / ikkiligi qanday?" for a plural / dual row, "To'g'ri javobni toping" for a row with an answer. "Start the test" begins one overall timer. Questions are shown to the whole class with A–D options (the row's wrong options, or other answers from the set) or as spoken questions with show-answer and correct / wrong. When the time runs out the screen shows "Time is up!" and the results. |
| **Word sets** (To'plamlar) | Import `.docx`, `.xlsx` (one set per sheet), `.txt` and `.csv`. Arabic and Uzbek text is sorted into the Word and Translation columns even when mixed or swapped, and a plural / dual written beside a word becomes a row of its own (see below). Edit rows inline and approve them; only approved rows are used. Rows from a file start approved, generated rows start unapproved. |
| **AI assistant** | *Engine (offline):* from a word list, builds the chosen dual / plural / singular form in a chosen case and state, with real forms of the same word as distractors. Ambiguous words are skipped with a reason. *Claude (online, optional):* drafts items on a topic with the teacher's Anthropic API key (`claude-opus-5-5`, structured output, server-side refusal fallback enabled). |
| Lexicon, Rules, About | Unchanged reference pages, now translated. |

The top navigation bar switches between **day**, **night** and **auto** (follows Windows) appearance.
The app version and the offline engine version (with rule / word counts) are shown in the footer. All text uses one bundled typeface — Noto Sans with its Arabic sibling — so it looks the same and works offline on every computer.

Sets and preferences are stored in the app's local storage on this computer.

## File format

Each row is one item: word or question, answer, note, wrong options. A header row
is recognised in Uzbek, Russian, English or Arabic (`So'z | Javob | Izoh | Variant 1 …`,
`Слово | Ответ | Примечание | Вариант 1 …`, `Word | Answer | Note | Option 1 …`,
`الكلمة | الجواب | ملاحظة | خيار 1 …`). Without a header the order is: prompt,
answer, wrong options. Text files may separate columns with `|`, Tab, `;` or ` — `;
lines starting with `#` are ignored. Translation columns are recognised as `Tarjima`, `Перевод`, `Translation`,
`الترجمة`; plural / dual columns as `Ko'pligi` / `Ikkiligi` (also `Plural`, `Dual`, Russian).

**Mixed Arabic and Uzbek** (`sidecar/vocab.py`): in a row without a header, Arabic
text goes to the word and Uzbek (Latin or Cyrillic) text to the translation, in
any order and even inside one cell — `كتاب – kitob`, `kitob | كتاب`, `كتاب kitob`.
Rows that read as a question or instruction (`?`, `«…»`, *toping*, *ko'plik*, more
than four words…) keep the positional order. Under a header, a row whose word and
translation are swapped is put right.

**Plurals and duals beside a word** become rows of their own, with `form` and the
`base` word, and are asked as "ko'pligi / ikkiligi qanday?" in the test:
`كِتَابٌ ج كُتُبٌ`, `بيت (ج) بيوت`, `بيت الجمع: بيوت`, `عين مثنى عينان`,
`kitob, ko'pligi | كتب`, or an unmarked `قلم (أقلام)` / `قلم / أقلام` that the
engine confirms (an unmarked bracket it cannot confirm is still taken as a plural
but flagged; an unmarked slash it cannot confirm is kept as synonyms). Their
translation is the one the teacher wrote next to it, otherwise it is made from
the word's: `kitob → kitoblar`, `ko'z → ikki ko'z` — such rows are flagged
"Tekshiring" for review. See `samples/lugat.txt`.

Old `.doc` / `.xls` files are refused with a
"save as .docx / .xlsx" message. Limits: 5 MB per file, 2000 rows, 300 characters per cell.

Sample files are in [`samples/`](samples/) (`lugat.txt` shows a mixed word list) (regenerate with
`python scripts/make_samples.py`).

```
desktop/
├── src/                    # Vue UI
│   ├── i18n/               # uz (reference shape), ar, ru, en
│   ├── views/              # Activity, Test, Sets, Lexicon, Rules, About
│   ├── components/         # SetPicker, AssistantPanel
│   ├── composables/        # drift-free pausable countdown
│   ├── stores/             # engine status, word sets (local storage)
│   └── claude.ts           # optional Claude drafting
├── sidecar/                # Python stdio service wrapping the engine
│   ├── importers.py        # .txt / .csv / .docx / .xlsx reader (standard library only)
│   ├── vocab.py            # Arabic / Uzbek sorting, plural and dual rows
│   ├── activity.py         # engine-built items with distractors
│   └── tests/
├── samples/                # namuna.txt / .xlsx / .docx
├── scripts/                # build-sidecar.ps1, make_samples.py, office_writer.py
└── src-tauri/              # Rust shell: spawns the service, exposes `engine_call`
```

## How it works

The Rust shell starts `arabmorph-service.exe` (the engine frozen with
PyInstaller) as a hidden child process. The two talk newline-delimited JSON
over stdin/stdout; no network port is opened. The service validates every
request itself rather than trusting the UI, and reads Office files with the
standard library only (zip + XML, sizes capped, DOCTYPE refused). If the
service dies, the shell restarts it once on the next request.

The only network access is the optional Claude assistant: the webview calls
`https://api.anthropic.com` directly (allowed by the CSP `connect-src`) with the
key the teacher enters. The key is kept only if "remember" is ticked, in plain
form in the app's local storage.

The installer includes the service, so end users don't need Python.

## Build requirements (development machine only)

- Python venv at the repo root with the engine installed (`pip install -e "engine[dev]"`)
- Node.js 18+
- Rust (stable, MSVC toolchain) and Visual Studio C++ Build Tools
- WebView2 runtime (preinstalled on Windows 10/11)

## Build

```powershell
cd desktop
npm install
npm run sidecar          # freeze the engine service (PyInstaller) and smoke-test it
npx tauri build          # → src-tauri/target/release/bundle/nsis/ArabMorph AI_0.4.0_x64-setup.exe
```

`npx tauri dev` runs the app with hot reload. Run `npm run sidecar` first, and
again whenever the engine or the sidecar changes.

## Tests

```powershell
..\.venv\Scripts\python -m pytest sidecar/tests   # service protocol, file import, generated items
npm run build                                      # vue-tsc type check (all four languages) + production build
```

## Installer notes

- NSIS, per-user install (`installMode: currentUser`): no administrator rights needed.
- The installer is **not code-signed**, so Windows SmartScreen may warn on
  first run ("More info → Run anyway"). Signing needs a certificate, which
  must never be committed (`.gitignore` excludes `*.pfx`, `*.p12`, `*.key`).
