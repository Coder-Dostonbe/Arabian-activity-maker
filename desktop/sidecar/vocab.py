"""Put Arabic words, Uzbek translations and the plural / dual written beside a word where they belong.

Teachers' word lists mix scripts freely - "كتاب – kitob", "kitob | كتاب", "كِتَابٌ ج كُتُبٌ – kitob",
"قلم (أقلام) qalam". This module sorts each piece into its place: the Arabic word goes to `prompt`,
the Uzbek (Latin or Cyrillic) meaning to `translation`, and every plural or dual written next to the
word becomes an item of its own, with its own translation ("kitoblar", "ikki kitob").

A form is taken as a plural or dual when it is marked (ج, جمع, مثنى, "ko'pligi", a "Ko'plik" column) or,
unmarked, when the engine confirms it is a plural or dual of the word. A translation this module had
to make up itself, or a form only the bracket convention vouched for, is flagged `uncertain`.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from arabmorph import Case, Number, PluralKind, Status, generate
from arabmorph.normalize import strip_diacritics

_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_OTHER = re.compile(r"[A-Za-zÀ-ɏЀ-ӿ]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_ARABIC_LETTER = re.compile(r"[ء-يٱ-ۓ]")

# Tokens: brackets and list separators stand alone so "(كُتُبٌ)" and "شيوخ، أشياخ" split cleanly.
_TOKEN = re.compile(r"[()\[\]/،,؛;]|[^\s()\[\]/،,؛;]+")
_SOFT = {"/", "،", ",", "؛", ";"}
_EDGE = " \t-–—:=|,،;؛/."

PLURAL_MARKERS = {"ج", "جج", "جمع", "الجمع", "جمعه", "جمعها"}
DUAL_MARKERS = {"مث", "مثنى", "المثنى", "مثناه"}
# Grammar labels a teacher puts in brackets after a word; they are a note, never a plural.
LABELS = {"م", "مذ", "مؤ", "مذكر", "مؤنث", "مفرد", "اسم", "فعل", "صفة", "حرف", "مصدر"}

_UZ_MARKERS = {
    "plural": {"koplik", "kopligi", "kopl", "kop", "jam", "jami", "plural", "pl", "мн", "мнч", "кўплик", "кўплиги", "кўпл"},
    "dual": {"ikkilik", "ikkiligi", "ikk", "dual", "du", "двч", "иккилик", "иккилиги"},
}
_MARKER_NOISE = re.compile(r"[\s'’ʻʼ`.:\-]+")

_QUESTION_WORDS = {
    "qaysi", "nima", "qanday", "nechta", "toping", "yozing", "tanlang", "ayting", "aniqlang", "keltiring",
    "какой", "какая", "какое", "какие", "найдите", "напишите", "выберите",
    "which", "what", "find", "write", "choose",
    # grammar terms: "«مهندس» — muzakkar solim ko'plik" asks for a form, it is not a translation
    "koplik", "kopligi", "kopligini", "ikkilik", "ikkiligi", "ikkiligini", "birlik", "birligi", "raf", "nasb",
    "jarr", "muzakkar", "muannas", "solim", "siniq", "izofa", "kelishik", "shakl", "shakli", "shaklini",
}
_WORDS = re.compile(r"[^\W\d_][\w'’ʻʼ`-]*")


def script(text: str) -> str:
    """"ar" for mostly-Arabic text, "uz" for mostly Latin / Cyrillic, "" for neither (digits, punctuation)."""
    ar, other = len(_ARABIC_LETTER.findall(text)), len(_OTHER.findall(text))
    if not ar and not other:
        return ""
    return "ar" if ar >= other else "uz"


def is_question(text: str) -> bool:
    """A question or instruction ("Kitobning ko'pligini toping"), as opposed to a short translation."""
    if re.search(r"[?؟«»\"“”]", text) or text.rstrip().endswith(":"):
        return True
    for s, part in segments(text):
        if s != "uz":
            continue  # Arabic words never make a question
        part, _ = uz_marker(part)  # "kitob, ko'pligi" announces a plural, it asks nothing
        for chunk in re.split(r"[,;]", part.casefold()):
            words = [_MARKER_NOISE.sub("", w) for w in _WORDS.findall(chunk)]
            if len(words) > 4 or any(w in _QUESTION_WORDS for w in words):
                return True
    return False


def _tidy(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\s+([،,;؛)\]])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    text = text.strip(_EDGE)
    if text.count("(") != text.count(")"):
        text = text.replace("(", "").replace(")", "").strip(_EDGE)
    return text


def segments(text: str) -> list[tuple[str, str]]:
    """Runs of one script: "كتاب – kitob" -> [("ar", "كتاب"), ("uz", "kitob")]."""
    tokens = text.split()
    out: list[list] = []
    pending: list[str] = []  # script-less tokens wait to see which side they belong to
    for tok in tokens:
        s = "ar" if _ARABIC.search(tok) and _ARABIC_LETTER.search(tok) else ("uz" if _OTHER.search(tok) else "")
        if not s:
            pending.append(tok)
            continue
        if out and out[-1][0] == s:
            out[-1][1].extend(pending)
            out[-1][1].append(tok)
        else:
            out.append([s, [tok]])
        pending = []
    if out and pending:
        out[-1][1].extend(pending)
    return [(s, t) for s, toks in out if (t := _tidy(" ".join(toks)))]


def _bare(tok: str) -> str:
    return tok.replace("ـ", "").strip(".:")


# --- engine check -------------------------------------------------------------

def _skeleton(text: str) -> str:
    s = strip_diacritics(unicodedata.normalize("NFC", text)).replace("ـ", "")
    for a in "أإآٱ":
        s = s.replace(a, "ا")
    s = re.sub(r"\s+", "", s)
    return s[2:] if s.startswith("ال") and len(s) > 4 else s


@lru_cache(maxsize=4096)
def relation(word: str, form: str) -> str | None:
    """"dual" or "plural" if the engine can produce `form` from `word`, else None."""
    target = _skeleton(form)
    if not target or target == _skeleton(word):
        return None
    plan = [(Number.DUAL, None)] + [(Number.PLURAL, k) for k in (None, PluralKind.SOUND_MASCULINE, PluralKind.SOUND_FEMININE)]
    for number, kind in plan:
        for case in Case:
            try:
                r = generate(word, number, case, kind=kind)
            except ValueError:
                return None
            if r.status is Status.ERROR:
                break
            if any(_skeleton(f.vocalized) == target for f in r.forms):
                return "dual" if number is Number.DUAL else "plural"
    return None


# --- Arabic cell: word + marked forms -------------------------------------------

def parse_arabic(text: str) -> tuple[str, list[dict], list[str]]:
    """Split "كِتَابٌ ج كُتُبٌ" / "قلم (أقلام)" / "يوم / أيام" into the word, its forms and bracketed labels.

    Each form is {"kind": "plural" | "dual", "text": ..., "certain": bool}.
    """
    base: list[str] = []
    forms: list[dict] = []
    labels: list[str] = []
    cur: dict | None = None  # the form being collected: kind None = not decided yet

    def close():
        nonlocal cur
        if cur is None:
            return
        body = _tidy(" ".join(cur["tokens"]))
        if body and cur["how"] == "paren" and cur["kind"] is None and body in LABELS:
            labels.append(body)
        elif body:
            forms.append({"kind": cur["kind"], "text": body, "how": cur["how"]})
        elif cur["how"] == "marker":
            return  # "كتاب (ج) كتب": the marker's bracket closed before the form - keep collecting
        cur = None

    for tok in _TOKEN.findall(text):
        bare = _bare(tok)
        if tok in "([":
            if base:
                close()
                cur = {"kind": None, "tokens": [], "how": "paren"}
            continue
        if tok in ")]":
            close()
            continue
        if base and (bare in PLURAL_MARKERS or bare in DUAL_MARKERS):
            kind = "plural" if bare in PLURAL_MARKERS else "dual"
            if cur is not None and not cur["tokens"]:
                cur.update(kind=kind, how="marker")
            else:
                close()
                cur = {"kind": kind, "tokens": [], "how": "marker"}
            continue
        if tok in _SOFT:
            if cur is not None:
                cur["tokens"].append("،")
            elif base:
                cur = {"kind": None, "tokens": [], "how": "soft"}
            continue
        (cur["tokens"] if cur is not None else base).append(tok)
    close()

    word = _tidy(" ".join(base))
    out: list[dict] = []
    for f in forms:
        if f["kind"] is not None:
            out.append({"kind": f["kind"], "text": f["text"], "certain": True})
            continue
        found = relation(word, f["text"].split("،")[0].strip()) if word else None
        if found:
            out.append({"kind": found, "text": f["text"], "certain": True})
        elif f["how"] == "paren":
            out.append({"kind": "plural", "text": f["text"], "certain": False})  # textbook convention: word (plural)
        else:
            word = f"{word}، {f['text']}"  # "a / b" the engine does not relate: synonyms, keep as written
    return word, out, labels


# --- Uzbek side -------------------------------------------------------------------

def uz_marker(text: str) -> tuple[str, str | None]:
    """Strip a trailing "ko'pligi" / "ikkiligi" from a translation: ("kitob", "plural")."""
    words = text.split()
    for kind, names in _UZ_MARKERS.items():
        if words and _MARKER_NOISE.sub("", words[-1].casefold()) in names:
            return _tidy(" ".join(words[:-1])), kind
    return text, None


def _meanings(text: str) -> list[str]:
    return [p for p in (s.strip() for s in re.split(r"[,;]", text)) if p]


def _split_tail(part: str) -> tuple[str, str]:
    m = re.match(r"^(.*?)(\s*\([^()]*\))?$", part)
    return (m.group(1), m.group(2) or "") if m else (part, "")


def uz_plural(text: str) -> str:
    """"kitob, asar" -> "kitoblar, asarlar"; verbs and words already in -lar are left alone."""
    out = []
    for part in _meanings(text):
        head, tail = _split_tail(part)
        words = head.split()
        if not words:
            out.append(part)
            continue
        last = words[-1].casefold()
        if re.search(r"(lar|ler|лар|moq|mak|моқ|мок)$", last):
            out.append(part)
            continue
        words[-1] += "лар" if _CYRILLIC.search(last) else "lar"
        out.append(" ".join(words) + tail)
    return ", ".join(out)


def uz_dual(text: str) -> str:
    """"kitob" -> "ikki kitob" (Uzbek keeps the noun singular after a numeral)."""
    out = []
    for part in _meanings(text):
        two = "икки" if _CYRILLIC.search(part) else "ikki"
        if part[:1].isupper() and not part[1:2].isupper():
            two, part = two.capitalize(), part[:1].lower() + part[1:]
        out.append(f"{two} {part}")
    return ", ".join(out)


# --- rows -> items ------------------------------------------------------------------

def _item(prompt: str, answer: str = "", note: str = "", options: list[str] | None = None,
          translation: str = "") -> dict:
    return {"prompt": prompt, "answer": answer, "note": note, "options": options or [], "translation": translation}


def _derived(word: str, translation: str, forms: list[dict], given: list[str]) -> list[dict]:
    """One item per plural / dual; `given` are translations the teacher wrote for them, in order."""
    out = []
    for i, f in enumerate(forms):
        explicit = f.get("translation") or (given[i] if i < len(given) else "")
        made = "" if explicit or not translation else (uz_plural if f["kind"] == "plural" else uz_dual)(translation)
        item = _item(f["text"], translation=explicit or made)
        item.update(form=f["kind"], base=word)
        if not f["certain"] or (made and not explicit):
            item["uncertain"] = True
        out.append(item)
    return out


def expand(fields: dict, options: list[str], forms_given: list[dict] | None = None) -> list[dict]:
    """Items from one row read by column roles: fix swapped / mixed scripts, split off marked forms."""
    prompt, translation = fields["prompt"], fields.get("translation", "")
    note = fields["note"]
    p_script, t_script = script(prompt), script(translation)
    if p_script == "uz" and t_script == "ar" and not is_question(prompt):
        prompt, translation = translation, prompt  # "kitob | كتاب" under "So'z | Tarjima"
    elif not translation and not fields["answer"] and not options and not is_question(prompt):
        parts = segments(prompt)
        ar = [t for s, t in parts if s == "ar"]
        uz = [t for s, t in parts if s == "uz"]
        if len(ar) == 1 and uz:
            prompt, translation = ar[0], ", ".join(uz)  # "كتاب kitob" in one cell

    forms = []
    for f in forms_given or []:  # a "Ko'pligi" cell may carry its own translation: "كُتُبٌ – kitoblar"
        parts = segments(f["text"])
        ar = ", ".join(t for sc, t in parts if sc == "ar")
        uz = ", ".join(t for sc, t in parts if sc == "uz")
        forms.append({**f, "text": ar or f["text"], "translation": uz if ar else ""})
    if script(prompt) == "ar" and not _OTHER.search(prompt) and not is_question(prompt):
        prompt, found, labels = parse_arabic(prompt)
        forms = found + forms
        if labels:
            note = ", ".join([note, *labels]) if note else ", ".join(labels)
    head = _item(prompt, fields["answer"], note, options, translation)
    return [head, *_derived(prompt, translation, forms, [])]


def split_row(cells: list[str]) -> list[dict] | None:
    """Items from a header-less row that mixes Arabic and Uzbek; None if the row is not a word entry.

    Order does not matter: "kitob | كتاب" and "كِتَابٌ ج كُتُبٌ – kitob" both give كتاب -> kitob (+ كتب -> kitoblar).
    """
    parts = [seg for c in cells for seg in segments(c)]
    if not any(s == "ar" for s, _ in parts) or not any(s == "uz" for s, _ in parts):
        return None
    if any(is_question(c) for c in cells):
        return None

    word: str | None = None
    forms: list[dict] = []
    labels: list[str] = []
    extra: list[str] = []
    uz: list[str] = []
    pending: str | None = None
    for s, text in parts:
        if s == "uz":
            text, pending = uz_marker(text)
            if text:
                uz.append(text)
            continue
        if word is not None and pending:
            forms.append({"kind": pending, "text": text, "certain": True})
            pending = None
            continue
        pending = None
        base, found, more = parse_arabic(text)
        labels += more
        if word is None:
            word = base
            forms += found
        elif kind := relation(word, base):
            forms.append({"kind": kind, "text": base, "certain": True})
        else:
            extra.append(text)
    if not word:
        return None

    translation = uz[0] if uz else ""
    given = uz[1:1 + len(forms)] if forms else []
    rest = uz[1 + len(given):]
    if not forms and rest:
        translation, rest = ", ".join(uz), []
    head = _item(word, extra[0] if extra else "", ", ".join([*labels, *rest]), extra[1:], translation)
    return [head, *_derived(word, translation, forms, given)]
