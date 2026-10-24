import base64
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sidecar"))
sys.path.insert(0, str(ROOT / "scripts"))
import arabmorph_service as svc  # noqa: E402
import importers  # noqa: E402
from importers import FileImportError, import_file  # noqa: E402
from office_writer import docx, xlsx  # noqa: E402


def items(result, n=0):
    return result["sets"][n]["items"]


def test_txt_with_header_and_pipes():
    text = "So'z | Javob | Izoh | Variant 1 | Variant 2\nكتاب | كِتَابَانِ | kitob | كِتَابَيْنِ | كُتُبٌ\n\nشجرة|شَجَرَتَانِ\n"
    r = import_file("dual.txt", text.encode("utf-8"))
    assert r["sets"][0]["name"] == "dual"
    first, second = items(r)
    assert first == {"prompt": "كتاب", "answer": "كِتَابَانِ", "note": "kitob", "options": ["كِتَابَيْنِ", "كُتُبٌ"]}
    assert second["answer"] == "شَجَرَتَانِ" and second["options"] == []


def test_txt_without_header_is_positional():
    r = import_file("w.txt", "كتاب\tكتابان\tكتابين\nقلم\tقلمان\n".encode("utf-8"))
    assert items(r)[0] == {"prompt": "كتاب", "answer": "كتابان", "note": "", "options": ["كتابين"]}


def test_txt_plain_word_list_and_numbering_and_comments():
    r = import_file("list.txt", "# words for lesson 3\n1. كتاب\n2) قلم\n".encode("utf-8"))
    assert [i["prompt"] for i in items(r)] == ["كتاب", "قلم"]
    assert all(i["answer"] == "" for i in items(r))


def test_txt_dash_separator():
    r = import_file("d.txt", "كتاب — كتابان\nقلم - قلمان\n".encode("utf-8"))
    assert [(i["prompt"], i["answer"]) for i in items(r)] == [("كتاب", "كتابان"), ("قلم", "قلمان")]


def test_txt_utf16_and_cp1256():
    assert items(import_file("a.txt", "كتاب|كتابان".encode("utf-16")))[0]["answer"] == "كتابان"
    assert items(import_file("b.txt", "كتاب|كتابان".encode("cp1256")))[0]["prompt"] == "كتاب"


def test_option_equal_to_answer_is_dropped():
    r = import_file("o.txt", "Savol|Javob|Variant|Variant\nX|A|A|B\n".encode("utf-8"))
    assert items(r)[0]["options"] == ["B"]


def test_csv():
    r = import_file("t.csv", "Question,Answer,Option 1\nكتاب,كتابان,كتابين\n".encode("utf-8"))
    assert items(r)[0] == {"prompt": "كتاب", "answer": "كتابان", "note": "", "options": ["كتابين"]}


def test_russian_and_arabic_headers():
    r = import_file("ru.txt", "Слово|Ответ|Перевод\nكتاب|كتابان|книга\n".encode("utf-8"))
    assert items(r)[0]["note"] == "книга"
    r = import_file("ar.txt", "الكلمة|الجواب|خيار 1\nكتاب|كتابان|كتابين\n".encode("utf-8"))
    assert items(r)[0]["options"] == ["كتابين"]


def test_xlsx_one_set_per_sheet():
    data = xlsx({
        "Ikkilik": [["So'z", "Javob"], ["كتاب", "كتابان"], ["", ""], ["قلم", "قلمان"]],
        "Test": [["Savol", "Javob", "Variant 1"], ["كتاب ning ko'pligi?", "كُتُب", "كتابات"]],
    })
    r = import_file("dars.xlsx", data)
    assert [s["name"] for s in r["sets"]] == ["dars — Ikkilik", "dars — Test"]
    assert [i["prompt"] for i in items(r, 0)] == ["كتاب", "قلم"]
    assert items(r, 1)[0]["options"] == ["كتابات"]


def test_xlsx_single_sheet_uses_file_name_and_shared_strings():
    # Excel itself stores text in sharedStrings.xml and numbers as plain values.
    buf = io.BytesIO()
    src = zipfile.ZipFile(io.BytesIO(xlsx({"Sheet1": [["x"]]})))
    with zipfile.ZipFile(buf, "w") as zf:
        for n in src.namelist():
            if n != "xl/worksheets/sheet1.xml":
                zf.writestr(n, src.read(n))
        zf.writestr("xl/sharedStrings.xml",
                    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    '<si><t>كتاب</t></si><si><r><t>كتا</t></r><r><t>بان</t></r></si></sst>')
        zf.writestr("xl/worksheets/sheet1.xml",
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="D1"><v>3.0</v></c></row>'
                    '</sheetData></worksheet>')
    r = import_file("one.xlsx", buf.getvalue())
    assert r["sets"][0]["name"] == "one"
    assert items(r)[0] == {"prompt": "كتاب", "answer": "كتابان", "note": "", "options": ["3"]}


def test_docx_tables_each_with_header_form_one_set():
    data = docx(paragraphs=["Dars 3"], tables=[
        [["So'z", "Javob"], ["كتاب", "كتابان"]],
        [["Savol", "Javob", "Izoh"], ["قلم", "قلمان", "ruchka"]],
    ])
    r = import_file("dars.docx", data)
    assert len(r["sets"]) == 1
    assert [(i["prompt"], i["note"]) for i in items(r)] == [("كتاب", ""), ("قلم", "ruchka")]


def test_docx_paragraphs_when_no_tables():
    r = import_file("p.docx", docx(paragraphs=["كتاب | كتابان", "", "قلم | قلمان"]))
    assert [i["answer"] for i in items(r)] == ["كتابان", "قلمان"]


@pytest.mark.parametrize("name,data,code", [
    ("old.doc", b"\xd0\xcf\x11\xe0", "legacy_format"),
    ("old.xls", b"\xd0\xcf\x11\xe0", "legacy_format"),
    ("pic.png", b"\x89PNG", "unsupported_format"),
    ("bad.docx", b"not a zip", "corrupt"),
    ("blank.txt", b"\n\n# only a comment\n", "empty"),
    ("big.txt", b"x" * (importers.MAX_FILE_BYTES + 1), "too_large"),
], ids=lambda v: v if isinstance(v, str) else "data")
def test_rejections(name, data, code):
    with pytest.raises(FileImportError) as exc:
        import_file(name, data)
    assert exc.value.code == code


def test_doctype_is_refused():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>')
    with pytest.raises(FileImportError) as exc:
        import_file("bomb.docx", buf.getvalue())
    assert exc.value.code == "corrupt"


def test_limits_are_reported():
    long = "ك" * (importers.MAX_FIELD + 50)
    r = import_file("l.txt", f"{long}|x\n".encode("utf-8"))
    assert len(items(r)[0]["prompt"]) == importers.MAX_FIELD and "field_truncated" in r["warnings"]
    many = "\n".join(f"w{i}|a" for i in range(importers.MAX_ITEMS + 5))
    r = import_file("m.txt", many.encode())
    assert len(items(r)) == importers.MAX_ITEMS and "items_limit" in r["warnings"]


def test_service_import_op():
    payload = base64.b64encode("كتاب|كتابان".encode("utf-8")).decode()
    r = svc.handle(json.dumps({"id": 1, "op": "import_file", "params": {"name": "a.txt", "data": payload}}))
    assert r["ok"] and r["result"]["sets"][0]["items"][0]["answer"] == "كتابان"
    r = svc.handle(json.dumps({"id": 2, "op": "import_file", "params": {"name": "a.doc", "data": payload}}))
    assert not r["ok"] and r["code"] == "legacy_format"
    r = svc.handle(json.dumps({"id": 3, "op": "import_file", "params": {"name": "a.txt", "data": "%%%"}}))
    assert not r["ok"] and r["code"] == "bad_request"
