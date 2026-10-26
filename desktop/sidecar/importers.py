"""Read activity items (prompt / answer / note / wrong options) from teacher files.

Supported: .txt, .csv/.tsv, .docx (tables or paragraphs) and .xlsx (one set per
sheet). Only the standard library is used - .docx and .xlsx are zip archives of
XML. Files are untrusted input: sizes are capped and XML carrying a DOCTYPE is
refused, so entity-expansion tricks never reach the parser.

Columns are found from a header row (So'z / Javob / Tarjima / Izoh / Ko'pligi /
Variant…, in Uzbek, Russian, English or Arabic). Without a header the order is:
prompt, answer, then wrong options - unless the row mixes Arabic and Uzbek, in
which case `vocab` sorts the pieces by script. Plurals and duals written beside
a word become items of their own (see `vocab`).
"""

from __future__ import annotations

import codecs
import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import PurePath

import vocab

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_MEMBER_BYTES = 30 * 1024 * 1024
MAX_ITEMS = 2000
MAX_FIELD = 300
MAX_OPTIONS = 6

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class FileImportError(ValueError):
    """An import failure the UI can explain; `code` is translated there."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# --- header recognition -------------------------------------------------------

_HEADERS = {
    "prompt": {
        "soz", "savol", "word", "question", "prompt", "term", "слово", "вопрос", "сўз", "савол",
        "كلمة", "الكلمة", "سؤال", "السؤال", "المفرد",
    },
    "answer": {
        "javob", "togrijavob", "answer", "correct", "correctanswer", "ответ", "правильныйответ", "жавоб",
        "جواب", "الجواب", "إجابة", "الإجابة", "اجابة", "الاجابة", "الإجابةالصحيحة", "المثنى", "الجمع",
    },
    "note": {
        "izoh", "note", "hint", "примечание", "подсказка", "изоҳ", "ملاحظة", "تلميح",
    },
    "translation": {
        "tarjima", "tarjimasi", "manosi", "mano", "uzbekcha", "ozbekcha", "translation", "meaning",
        "перевод", "значение", "таржима", "маъноси", "ўзбекча", "ترجمة", "الترجمة", "المعنى",
    },
    # A plural / dual column next to the word: each cell becomes an item of its own.
    "plural": {
        "koplik", "kopligi", "jam", "jami", "plural", "множественное", "множественноечисло", "мнч",
        "кўплик", "кўплиги",
    },
    "dual": {"ikkilik", "ikkiligi", "dual", "двойственное", "двойственноечисло", "иккилик", "иккилиги"},
}
_OPTION_PREFIXES = ("variant", "option", "choice", "wrong", "notogri", "вариант", "خيار", "الخيار", "بديل")
_NOISE = re.compile(r"[\s'’ʻʼ`\"_.:#№()\-\d]+")


def _header_role(cell: str) -> str | None:
    key = _NOISE.sub("", cell.casefold())
    if not key:
        return None
    for role, names in _HEADERS.items():
        if key in names:
            return role
    if key.startswith(_OPTION_PREFIXES):
        return "option"
    return None


def _header_map(row: list[str]) -> dict[int, str] | None:
    """Column roles if `row` is a header row, else None."""
    cells = [(i, c) for i, c in enumerate(row) if c.strip()]
    if not cells:
        return None
    roles = {i: _header_role(c) for i, c in cells}
    known = {i: r for i, r in roles.items() if r}
    if len(known) < min(2, len(cells)):
        return None
    return known


# --- rows -> items ------------------------------------------------------------

def _clip(text: str, warnings: set[str]) -> str:
    text = " ".join(text.split())
    if len(text) > MAX_FIELD:
        warnings.add("field_truncated")
        text = text[:MAX_FIELD]
    return text


def _items(rows: list[list[str]], warnings: set[str]) -> list[dict]:
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return []
    roles = _header_map(rows[0])
    if roles is not None:
        rows = rows[1:]
        if "prompt" not in roles.values():
            roles[0] = "prompt"  # e.g. an unnamed first column before "Javob"
    items = []
    for row in rows:
        if roles is None:
            mixed = vocab.split_row([_clip(c, warnings) for c in row])
            if mixed is not None:
                items.extend(_dedupe(i) for i in mixed)
                continue
        fields = {"prompt": "", "answer": "", "note": "", "translation": ""}
        options: list[str] = []
        forms: list[dict] = []
        for i, cell in enumerate(row):
            role = roles.get(i) if roles is not None else ("prompt", "answer")[i] if i < 2 else "option"
            value = _clip(cell, warnings)
            if not role or not value:
                continue
            if role == "option":
                options.append(value)
            elif role in ("plural", "dual"):
                forms.append({"kind": role, "text": value, "certain": True})
            elif not fields[role]:
                fields[role] = value
        if not fields["prompt"]:
            continue
        items.extend(_dedupe(i) for i in vocab.expand(fields, options, forms))
    return items


def _dedupe(item: dict) -> dict:
    item["options"] = [o for o in dict.fromkeys(item["options"]) if o != item["answer"]][:MAX_OPTIONS]
    return item


# --- plain text ---------------------------------------------------------------

_DELIMITERS = ("\t", "|", ";")
_DASH = re.compile(r"\s+[—–-]\s+")
_NUMBERING = re.compile(r"^\s*\d{1,3}[.)]\s+")


def _lines_to_rows(lines: list[str]) -> list[list[str]]:
    lines = [_NUMBERING.sub("", l).strip() for l in lines]
    lines = [l for l in lines if l and not l.startswith("#")]
    counts = {d: sum(d in l for l in lines) for d in _DELIMITERS}
    best = max(_DELIMITERS, key=lambda d: counts[d])  # ties keep the earlier delimiter
    if counts[best]:
        return [[c.strip() for c in l.split(best)] for l in lines]
    if any(_DASH.search(l) for l in lines):
        return [[c.strip() for c in _DASH.split(l)] for l in lines]
    return [[l] for l in lines]


def _decode(data: bytes) -> str:
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    # Legacy Windows code pages: pick the one that yields more letters of its own script.
    arabic = data.decode("cp1256", errors="replace")
    cyrillic = data.decode("cp1251", errors="replace")
    score_ar = len(re.findall(r"[؀-ۿ]", arabic))
    score_cy = len(re.findall(r"[Ѐ-ӿ]", cyrillic))
    return arabic if score_ar >= score_cy else cyrillic


def _csv_rows(text: str) -> list[list[str]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [row for row in csv.reader(io.StringIO(text), dialect)]


# --- Office files ---------------------------------------------------------------

def _xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        info = zf.getinfo(name)
    except KeyError:
        raise FileImportError("corrupt", f"missing part {name}") from None
    if info.file_size > MAX_MEMBER_BYTES:
        raise FileImportError("too_large", f"part {name} is too large")
    data = zf.read(info)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise FileImportError("corrupt", "XML with a DOCTYPE is not accepted")
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        raise FileImportError("corrupt", f"part {name} is not valid XML") from None


def _paragraph_text(p: ET.Element) -> str:
    out = []
    for el in p.iter():
        if el.tag == W + "t" and el.text:
            out.append(el.text)
        elif el.tag == W + "tab":
            out.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            out.append(" ")
    return "".join(out)


def _docx_rows(zf: zipfile.ZipFile) -> list[list[list[str]]]:
    """One row list per table; if the document has no tables, its paragraphs as lines."""
    body = _xml(zf, "word/document.xml").find(W + "body")
    if body is None:
        return []
    tables = []
    for tbl in body.iter(W + "tbl"):
        rows = [[" ".join(_paragraph_text(p) for p in tc.iter(W + "p")) for tc in tr.findall(W + "tc")]
                for tr in tbl.findall(W + "tr")]
        if rows:
            tables.append(rows)
    if tables:
        return tables
    return [_lines_to_rows([_paragraph_text(p) for p in body.iter(W + "p")])]


def _column_index(ref: str) -> int:
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _xlsx_sheets(zf: zipfile.ZipFile) -> list[tuple[str, list[list[str]]]]:
    workbook = _xml(zf, "xl/workbook.xml")
    rels = _xml(zf, "xl/_rels/workbook.xml.rels")
    targets = {r.get("Id"): r.get("Target", "") for r in rels.iter(PR + "Relationship")}
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        for si in _xml(zf, "xl/sharedStrings.xml").iter(S + "si"):
            shared.append("".join(t.text or "" for t in si.iter(S + "t")))
    sheets = []
    for sheet in workbook.iter(S + "sheet"):
        target = targets.get(sheet.get(R + "id"), "")
        path = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        rows = []
        for row in _xml(zf, path).iter(S + "row"):
            cells: dict[int, str] = {}
            for pos, c in enumerate(row.findall(S + "c")):
                col = _column_index(c.get("r", "")) if c.get("r") else pos
                kind, v = c.get("t"), c.find(S + "v")
                if kind == "s" and v is not None and (v.text or "").isdigit() and int(v.text) < len(shared):
                    value = shared[int(v.text)]
                elif kind == "inlineStr":
                    value = "".join(t.text or "" for t in c.iter(S + "t"))
                elif kind == "b" and v is not None:
                    value = "TRUE" if v.text == "1" else "FALSE"
                elif v is not None and v.text:
                    value = v.text
                    if kind is None:
                        try:
                            f = float(value)
                            value = str(int(f)) if f.is_integer() else value
                        except ValueError:
                            pass
                else:
                    value = ""
                if col >= 0:
                    cells[col] = value
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        sheets.append((sheet.get("name") or "", rows))
    return sheets


def _open_zip(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise FileImportError("corrupt", "the file is not a valid Office document") from None


# --- entry point ------------------------------------------------------------------

def import_file(name: str, data: bytes) -> dict:
    """Parse one file into sets of items: {"sets": [{"name", "items"}], "warnings": [codes]}."""
    if len(data) > MAX_FILE_BYTES:
        raise FileImportError("too_large", f"files are limited to {MAX_FILE_BYTES // (1024 * 1024)} MB")
    path = PurePath(name)
    stem, ext = path.stem or "import", path.suffix.lower().lstrip(".")
    if ext in ("doc", "xls", "rtf", "odt", "ods"):
        raise FileImportError("legacy_format", f".{ext} is not supported; save the file as .docx or .xlsx")
    if ext in ("txt", "text"):
        tables = [(stem, _lines_to_rows(_decode(data).splitlines()))]
    elif ext in ("csv", "tsv"):
        tables = [(stem, _csv_rows(_decode(data)))]
    elif ext == "docx":
        # All tables of a document form one set; each table keeps its own header row.
        with _open_zip(data) as zf:
            tables = [(stem, rows) for rows in _docx_rows(zf)]
    elif ext in ("xlsx", "xlsm"):
        with _open_zip(data) as zf:
            tables = [(f"{stem} — {sheet}" if sheet else stem, rows) for sheet, rows in _xlsx_sheets(zf)]
        if len(tables) == 1:
            tables = [(stem, tables[0][1])]
    else:
        raise FileImportError("unsupported_format", f"unsupported file type '.{ext}'")

    warnings: set[str] = set()
    grouped: dict[str, list[dict]] = {}
    total = 0
    for set_name, rows in tables:
        items = _items(rows, warnings)
        if total + len(items) > MAX_ITEMS:
            items = items[: MAX_ITEMS - total]
            warnings.add("items_limit")
        if items:
            grouped.setdefault(set_name, []).extend(items)
            total += len(items)
    sets = [{"name": n, "items": items} for n, items in grouped.items()]
    if not sets:
        raise FileImportError("empty", "no rows with a word or question were found")
    return {"sets": sets, "warnings": sorted(warnings)}
