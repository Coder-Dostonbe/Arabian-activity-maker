# ArabMorph AI — Windows desktop app

A classroom app for Arabic lessons, built with Tauri 2 + Vue 3 + TypeScript around
the offline `arabmorph` engine. The interface is in Uzbek, Arabic (RTL), Russian
and English; the language is switched in the UI and remembered on the computer.

## Sections

| Section | What it does |
| ------- | ------------ |
| **Activity** (Mashg'ulot) | Choose a direction: **Arabic → Uzbek** (the Arabic word is shown, its translation is the answer), **Uzbek → Arabic**, or **Word → answer** (the row's own answer, for grammar sets). Approved words appear one at a time, each for a set number of seconds, then the next word appears automatically. Correct / wrong buttons (keys 1 / 2) move on early; an optional pause shows the answer. A summary lists missed words and can repeat them. After a wrong answer or "show answer" on a row the engine built, the rule behind the correct form (name, explanation, example) is shown. |
| **Test** | Questions are always worded in Uzbek: "Bu so'z o'zbekchada nima degani?" for a word with a translation, "Bu so'zning ko'pligi / ikkiligi qanday?" for a plural / dual row, "To'g'ri javobni toping" for a row with an answer. "Start the test" begins one overall timer. Questions are shown to the whole class with A–D options (the row's wrong options, or other answers from the set) or as spoken questions with show-answer and correct / wrong. When the time runs out the screen shows "Time is up!" and the results. Engine-built rows show their rule after a wrong answer or "show answer". Each finished test is saved with an optional class / group name. |
| **Word sets** (To'plamlar) | Import `.docx`, `.xlsx` (one set per sheet), `.txt` and `.csv`. Arabic and Uzbek text is sorted into the Word and Translation columns even when mixed or swapped, and a plural / dual written beside a word becomes a row of its own (see below). Edit rows inline and approve them; only approved rows are used. Rows from a file start approved, generated rows start unapproved. Claude's rows carry the engine's verdict as a badge (agrees / differs, with the engine's form / not checkable); "Approve all" skips rows the engine disagrees with. |
| **AI assistant** | *Engine (offline):* from a word list, builds the chosen dual / plural / singular form in a chosen case and state. Distractors are another case or state of the same word plus rule errors — the sound plural for a broken one (`كتابات`), the suffix added without the required change (`صحراءان`, `مستشفاان`), a case vowel no case uses — and never a correct form. Ambiguous words are skipped with a reason. *Claude (online, optional):* drafts items on a topic with the teacher's Anthropic API key and the chosen model — Claude Haiku 5.5 (default, cheapest), Sonnet 5.5 or Opus 5.5, with a cost hint; structured output; server-side refusal fallback on Sonnet and Opus. Every drafted item is re-checked by the engine (see Word sets). |
| **Analysis** (Tahlil) | Type a word: its singular, dual and plural forms in 3 cases × 3 states, each with source, confidence, condition, warnings and the rules (Arabic / English explanation). The word as typed is also analysed backwards (which singular, number, case, state), with "did you mean" suggestions. For a word the lexicon does not know, **Ask Claude** proposes a lexicon entry. |
| **Results** (Natijalar) | History of finished tests (date, set, group, score, each question's outcome), filter by group, mistakes per engine rule, export to `.xlsx`. |
| **Lexicon** | The bundled entries plus the teacher's own. Claude's proposals wait in a **review queue**, are checked against the lexicon schema, and on approval go to `lexicon_user.json` (`verified: false`, `source: "user"`), which the engine loads with the seed. |
| Rules, About | Reference pages; About opens the log folder. |

The top navigation bar switches between **day**, **night** and **auto** (follows Windows) appearance.
The app version and the offline engine version (with rule / word counts) are shown in the footer. All text uses one bundled typeface — Noto Sans with its Arabic sibling — so it looks the same and works offline on every computer.

Sets and preferences are saved as files in the app's data folder on this computer (see *Saved data* below).

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
│   ├── views/              # Activity, Test, Sets, Analysis, Results, Lexicon, Rules, About
│   ├── components/         # SetPicker, AssistantPanel
│   ├── composables/        # drift-free pausable countdown
│   ├── stores/             # engine status, word sets
│   ├── storage.ts          # saved files (via the Rust shell), migration from local storage
│   └── claude.ts           # optional Claude drafting (request made in Rust)
├── sidecar/                # Python stdio service wrapping the engine
│   ├── importers.py        # .txt / .csv / .docx / .xlsx reader (standard library only)
│   ├── vocab.py            # Arabic / Uzbek sorting, plural and dual rows
│   ├── activity.py         # engine-built items with case/state and rule-error distractors
│   ├── verify.py           # re-checks Claude's items with the engine
│   ├── user_lexicon.py     # the teacher's own lexicon entries (lexicon_user.json)
│   ├── office_writer.py    # minimal .xlsx / .docx writer (results export, samples, tests)
│   └── tests/
├── samples/                # namuna.txt / .xlsx / .docx
├── scripts/                # build-sidecar.ps1, make_samples.py
└── src-tauri/              # Rust shell: service + timeouts, log, data files, API key, Claude request
```

## How it works

The Rust shell starts `arabmorph-service.exe` (the engine frozen with
PyInstaller `--onedir`, bundled as the `arabmorph-service/` resource folder) as a
hidden child process. The two talk newline-delimited JSON over stdin/stdout; no
network port is opened. The service validates every request itself rather than
trusting the UI, and reads Office files with the standard library only (zip + XML,
sizes capped, DOCTYPE refused).

Each request has a timeout (15 s, 60 s for a file import). On a timeout the shell
kills the service and returns an error; the next request starts a fresh one. If
the service dies, the shell restarts it once and retries. The service's stderr —
including the full traceback of any internal error, whose reply to the UI stays
generic — goes to `arabmorph-service.log` (rotated at 1 MB, three old files kept)
in `%LOCALAPPDATA%\ai.arabmorph.desktop\logs`; **About → Open log folder** opens it.

Service operations (`sidecar/arabmorph_service.py`, `OPS`): `version`,
`generate`, `paradigm`, `analyze`, `rules`, `lexicon`, `import_file`,
`build_items`, `verify_items` (re-check Claude's items), `user_lexicon`,
`user_lexicon_check`, `user_lexicon_add`, `user_lexicon_remove` (the teacher's
own entries in `%APPDATA%\ai.arabmorph.desktop\data\lexicon_user.json`) and
`export_xlsx` (test results).

**Saved data.** Word sets, settings, test results (`results.json`) and the lexicon review queue (`lexicon_queue.json`) are JSON files in
`%APPDATA%\ai.arabmorph.desktop\data` (`sets.json`, `settings.json`). Each save is
debounced (500 ms), written to a temporary file and renamed over the old one, and
the previous version is kept in `data\backups` (the last 5). If a file cannot be
read, the newest readable backup is loaded and the Word sets page says so. On
the first start of this version, data kept by older versions in the webview's
local storage is copied over (the old copy is left in place). **Word sets →
Export all** writes one `ArabMorph-backup-<time>.json` with every set and setting
to the Downloads folder; **Import backup** restores such a file (sets with the
same id are replaced, others are added).

The only network access is the optional Claude assistant. The request is made by
the Rust shell (`src-tauri/src/claude.rs`), so the webview's CSP allows no
external host at all. If "remember" is ticked, the API key is stored in Windows
Credential Manager (entry "ArabMorph AI"); the key is never returned to the
webview. A key that an older version saved in local storage is moved there on
the first start.

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
npm run sidecar          # freeze the engine service (PyInstaller --onedir) and smoke-test it
npx tauri build          # → src-tauri/target/release/bundle/nsis/ArabMorph AI_0.5.0_x64-setup.exe
```

`npx tauri dev` runs the app with hot reload. Run `npm run sidecar` first, and
again whenever the engine or the sidecar changes.

## Tests

```powershell
..\.venv\Scripts\python -m pytest sidecar/tests   # service protocol, file import, generated items
cargo test --manifest-path src-tauri/Cargo.toml    # timeouts, log rotation, atomic saves and backups
npm run build                                      # vue-tsc type check (all four languages) + production build
```

The same checks run in CI (`.github/workflows/ci.yml`) on Windows, with
`cargo check` both without and with the `updater` feature.

## Updates (prepared, not active)

`tauri-plugin-updater` sits behind the Cargo feature `updater`, which is off,
so normal builds contain no updater. `src-tauri/tauri.updater.conf.json` holds
its settings: the GitHub Releases `latest.json` endpoint, passive install, and
updater artifacts. Its `pubkey` is a placeholder. To turn it on:

1. `npx tauri signer generate -w <path outside the repo>`, then put the
   **public** key into `pubkey`. The private key and its password are never
   committed.
2. Build with the key in the environment (`TAURI_SIGNING_PRIVATE_KEY`,
   `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`):
   `npx tauri build --features updater --config src-tauri/tauri.updater.conf.json`.
3. Upload the installer, its `.sig` and a `latest.json` to the GitHub release.
4. Add the update check to the UI (`@tauri-apps/plugin-updater` and the
   `updater:default` capability).

## Installer notes

- NSIS, per-user install (`installMode: currentUser`): no administrator rights needed.
- The installer is **not code-signed**, so Windows SmartScreen may warn on
  first run ("More info → Run anyway"). Signing needs a certificate, which
  must never be committed (`.gitignore` excludes `*.pfx`, `*.p12`, `*.key`).
