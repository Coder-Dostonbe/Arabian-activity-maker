import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sidecar"))
import vocab  # noqa: E402
from importers import import_file  # noqa: E402


def rows(text: str, name: str = "w.txt"):
    return import_file(name, text.encode("utf-8"))["sets"][0]["items"]


def pairs(items):
    return [(i["prompt"], i["translation"]) for i in items]


@pytest.mark.parametrize("line", ["كتاب – kitob", "kitob – كتاب", "كتاب | kitob", "kitob\tكتاب", "كتاب kitob", "kitob كتاب"])
def test_arabic_and_uzbek_find_their_places_in_any_order(line):
    (item,) = rows(line)
    assert (item["prompt"], item["translation"], item["answer"]) == ("كتاب", "kitob", "")


def test_mixed_file_rows_are_sorted_one_by_one():
    items = rows("كتاب | kitob\nqalam | قلم\nبيت – uy, xona\n")
    assert pairs(items) == [("كتاب", "kitob"), ("قلم", "qalam"), ("بيت", "uy, xona")]


def test_cyrillic_uzbek_is_a_translation_too():
    assert pairs(rows("китоб – كتاب")) == [("كتاب", "китоб")]


def test_marked_plural_becomes_its_own_item_with_translation():
    word, plural = rows("كِتَابٌ ج كُتُبٌ – kitob")
    assert (word["prompt"], word["translation"]) == ("كِتَابٌ", "kitob")
    assert "form" not in word
    assert (plural["prompt"], plural["translation"], plural["form"], plural["base"]) == ("كُتُبٌ", "kitoblar", "plural", "كِتَابٌ")
    assert plural["uncertain"]  # "kitoblar" was made up, the teacher checks it


@pytest.mark.parametrize("line", [
    "كِتَابٌ ج كُتُبٌ – kitob, kitoblar",
    "كِتَابٌ ج كُتُبٌ – kitob – kitoblar",
    "كِتَابٌ ج كُتُبٌ – kitob / kitoblar",
    "kitob, kitoblar – كِتَابٌ ج كُتُبٌ",
    "كِتَابٌ ج كُتُبٌ – kitoblar, kitob",
])
def test_plural_translation_in_the_word_cell_goes_to_the_plural(line):
    # Regression: the singular was "kitob, kitoblar" and the plural "kitoblar, kitoblar".
    word, plural = rows(line)
    assert (word["translation"], plural["translation"]) == ("kitob", "kitoblar")
    assert "uncertain" not in plural  # the teacher wrote it


def test_dual_translation_in_the_word_cell_goes_to_the_dual():
    word, dual = rows("عَيْنٌ مثنى عَيْنَانِ – ko'z, ikki ko'z")
    assert (word["translation"], dual["translation"]) == ("ko'z", "ikki ko'z")


def test_other_meanings_stay_with_the_word():
    word, plural = rows("بَيْتٌ ج بُيُوتٌ – uy, xona, uylar")
    assert (word["translation"], plural["translation"]) == ("uy, xona", "uylar")


def test_plural_translation_in_the_word_cell_of_a_multi_line_file():
    items = rows("كِتَابٌ ج كُتُبٌ – kitob – kitoblar\nقَلَمٌ ج أَقْلَامٌ – qalam\n")
    assert pairs(items) == [("كِتَابٌ", "kitob"), ("كُتُبٌ", "kitoblar"), ("قَلَمٌ", "qalam"), ("أَقْلَامٌ", "qalamlar")]


def test_plural_translation_without_a_plural_form_is_kept():
    (word,) = rows("كِتَابٌ – kitob, kitoblar")
    assert word["translation"] == "kitob, kitoblar"


@pytest.mark.parametrize("cell", ["بيت ج بيوت", "بيت ج. بيوت", "بيت جـ بيوت", "بيت (ج) بيوت", "بيت (ج بيوت)", "بيت الجمع: بيوت"])
def test_plural_marker_spellings(cell):
    assert [(i["prompt"], i.get("form")) for i in rows(f"{cell} – uy")] == [("بيت", None), ("بيوت", "plural")]


def test_teacher_written_plural_translation_is_used_and_trusted():
    word, plural = rows("طالب ج طلاب | talaba | talabalar")
    assert plural["translation"] == "talabalar" and "uncertain" not in plural


def test_several_plurals_stay_together():
    _, plural = rows("شيخ ج شيوخ، أشياخ - chol")
    assert plural["prompt"] == "شيوخ، أشياخ" and plural["translation"] == "chollar"


def test_bracketed_plural_is_confirmed_by_the_engine():
    _, plural = rows("قلم (أقلام) – qalam")
    assert plural["form"] == "plural" and plural["base"] == "قلم"


def test_bracketed_dual_is_recognised_as_dual():
    _, dual = rows("كتاب (كتابان) – kitob")
    assert (dual["form"], dual["translation"]) == ("dual", "ikki kitob")


def test_dual_marker_and_uzbek_markers():
    _, dual = rows("عين مثنى عينان – ko'z")
    assert (dual["prompt"], dual["form"], dual["translation"]) == ("عينان", "dual", "ikki ko'z")
    word, plural = rows("كتاب | kitob, ko'pligi | كتب")
    assert (word["translation"], plural["prompt"], plural["form"]) == ("kitob", "كتب", "plural")


def test_unrelated_slash_is_kept_as_written():
    # The engine does not relate the two, so they are synonyms, not a plural.
    assert pairs(rows("سيارة / عربة – mashina")) == [("سيارة، عربة", "mashina")]


def test_engine_confirmed_slash_pair_is_split():
    assert [i.get("form") for i in rows("قلم / أقلام – qalam")] == [None, "plural"]


def test_grammar_label_in_brackets_goes_to_note():
    (item,) = rows("رجل (مذكر) – erkak")
    assert (item["prompt"], item["note"], item["translation"]) == ("رجل", "مذكر", "erkak")


@pytest.mark.parametrize("line", ["Kitobning ko'pligini toping | كُتُب", "كتاب ning ko'pligi? | كُتُب", "Qaysi biri ikkilik | كتابان"])
def test_questions_keep_the_column_order(line):
    (item,) = rows(line)
    assert item["answer"] == "كُتُب" or item["answer"] == "كتابان"
    assert item["translation"] == ""


def test_all_arabic_rows_are_unchanged():
    (item,) = rows("كتاب | كتابان | كتابين")
    assert (item["prompt"], item["answer"], item["options"]) == ("كتاب", "كتابان", ["كتابين"])


def test_header_columns_swapped_on_some_rows():
    items = rows("So'z | Tarjima\nكتاب | kitob\nkalit | مفتاح\n")
    assert pairs(items) == [("كتاب", "kitob"), ("مفتاح", "kalit")]


def test_plural_column_with_its_own_translation():
    items = rows("So'z | Ko'pligi | Tarjima\nكتاب | كُتُبٌ – kitoblar | kitob\nقلم | أقلام | qalam\n")
    assert [(i["prompt"], i["translation"], i.get("form")) for i in items] == [
        ("كتاب", "kitob", None), ("كُتُبٌ", "kitoblar", "plural"),
        ("قلم", "qalam", None), ("أقلام", "qalamlar", "plural"),
    ]
    assert "uncertain" not in items[1] and items[3]["uncertain"]


def test_dual_column():
    items = rows("Word | Dual | Translation\nكتاب | كتابان | kitob\n")
    assert [(i["prompt"], i["translation"], i.get("form")) for i in items] == [("كتاب", "kitob", None), ("كتابان", "ikki kitob", "dual")]


def test_arabic_only_word_list_with_marker_is_split():
    assert [(i["prompt"], i.get("form")) for i in rows("كتاب ج كتب\n")] == [("كتاب", None), ("كتب", "plural")]


@pytest.mark.parametrize("text,plural", [
    ("kitob", "kitoblar"),
    ("uy, xona", "uylar, xonalar"),
    ("qizil olma", "qizil olmalar"),
    ("kitob (darslik)", "kitoblar (darslik)"),
    ("китоб", "китоблар"),
    ("odamlar", "odamlar"),
    ("o'qimoq", "o'qimoq"),
    ("kitob, kitoblar", "kitoblar"),
])
def test_uz_plural(text, plural):
    assert vocab.uz_plural(text) == plural


def test_uz_dual():
    assert vocab.uz_dual("kitob") == "ikki kitob"
    assert vocab.uz_dual("Ko'z, qo'l") == "Ikki ko'z, ikki qo'l"
    assert vocab.uz_dual("китоб") == "икки китоб"


def test_script_and_question_helpers():
    assert vocab.script("كِتَابٌ") == "ar" and vocab.script("kitob") == "uz" and vocab.script("123") == ""
    assert vocab.is_question("Kitobning ko'pligini toping") and vocab.is_question("ما جمع كتاب؟")
    assert not vocab.is_question("uy, xona, bino") and not vocab.is_question("كِتَابٌ ج كُتُبٌ")


def test_grammar_instruction_rows_are_not_mistaken_for_translations():
    (item,) = rows("«مهندس» — muzakkar solim ko'plik | مُهَنْدِسُونَ")
    assert (item["answer"], item["translation"]) == ("مُهَنْدِسُونَ", "")
    (item,) = rows("Savol | Javob | Variant 1\n«مهندس» — muzakkar solim ko'plik, raf' | مُهَنْدِسُونَ | مُهَنْدِسِينَ\n")
    assert item["prompt"].startswith("«مهندس»") and item["translation"] == ""


def test_shipped_samples_import_unchanged():
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_samples
    from office_writer import xlsx
    r = import_file("namuna.xlsx", xlsx({"Ikkilik": make_samples.DUAL, "Test": make_samples.TEST}))
    for s, src in zip(r["sets"], (make_samples.DUAL, make_samples.TEST)):
        assert [i["prompt"] for i in s["items"]] == [row[0] for row in src[1:]]
        assert all(i["translation"] == "" and "form" not in i for i in s["items"])


@pytest.mark.parametrize("arabic", ["ﻛﺘﺎﺏ", "مستشفی", "کتاب"])
def test_spellings_the_engine_folds_count_as_arabic(arabic):
    assert vocab.script(arabic) == "ar"
    assert pairs(rows(f"{arabic} – kitob")) == [(arabic, "kitob")]
