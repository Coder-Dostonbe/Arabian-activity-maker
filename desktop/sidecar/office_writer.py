"""Minimal .docx / .xlsx writers (standard library only).

Used for the results export (.xlsx), the sample files in desktop/samples/ and the sidecar test fixtures,
so both exercise the same Office structure the importer reads.
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

_CT = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def _zip(parts: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in parts.items():
            zf.writestr(name, text)
    return buf.getvalue()


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx(sheets: dict[str, list[list[str]]]) -> bytes:
    """Workbook with one sheet per entry; cells are inline strings."""
    names = list(sheets)
    parts = {
        "[Content_Types].xml": _CT + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                      for i in range(len(names)))
            + "</Types>"),
        "_rels/.rels": _CT + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"),
        "xl/workbook.xml": _CT + (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names))
            + "</sheets></workbook>"),
        "xl/_rels/workbook.xml.rels": _CT + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                      for i in range(len(names)))
            + "</Relationships>"),
    }
    for i, rows in enumerate(sheets.values()):
        body = "".join(
            f'<row r="{r + 1}">' + "".join(
                f'<c r="{_col(c)}{r + 1}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
                for c, v in enumerate(row) if v)
            + "</row>"
            for r, row in enumerate(rows))
        parts[f"xl/worksheets/sheet{i + 1}.xml"] = _CT + (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{body}</sheetData></worksheet>")
    return _zip(parts)


def docx(paragraphs: list[str] = (), tables: list[list[list[str]]] = ()) -> bytes:
    """Document with the given paragraphs followed by the given tables."""
    def p(text: str) -> str:
        return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'

    body = "".join(p(t) for t in paragraphs)
    for table in tables:
        body += "<w:tbl>" + "".join(
            "<w:tr>" + "".join(f"<w:tc>{p(cell)}</w:tc>" for cell in row) + "</w:tr>" for row in table
        ) + "</w:tbl>"
    return _zip({
        "[Content_Types].xml": _CT + (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"),
        "_rels/.rels": _CT + (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"),
        "word/document.xml": _CT + (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>"),
    })
