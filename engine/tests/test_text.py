"""Normalisation, cluster and input-parsing tests."""

import unicodedata

import pytest

from arabmorph import NormalizationOptions, normalize, strip_diacritics
from arabmorph.clusters import bare, join_clusters, split_clusters
from arabmorph.noun_input import InputError, parse_noun


def nfc(s):
    return unicodedata.normalize("NFC", s)


class TestNormalize:
    def test_original_is_preserved(self):
        r = normalize("كِتَابٌ", NormalizationOptions(strip_diacritics=True))
        assert r.original == "كِتَابٌ"
        assert r.normalized == "كتاب"

    def test_default_keeps_diacritics_and_removes_tatweel(self):
        assert normalize("كـتَـاب").normalized == nfc("كتَاب")

    def test_strip_diacritics_keeps_hamza_letters(self):
        assert strip_diacritics("مَبْدَأٌ") == "مبدأ"
        assert strip_diacritics("إِنْشَاءٌ") == "إنشاء"
        assert strip_diacritics("آمَنَ") == "آمن"

    def test_lossy_options_are_off_by_default_and_flagged_when_on(self):
        assert not normalize("مستشفى").lossy
        r = normalize("أحمد مستشفى مدرسة", NormalizationOptions(
            unify_alef=True, alef_maqsura_to_yeh=True, teh_marbuta_to_heh=True))
        assert r.lossy
        assert r.normalized == "احمد مستشفي مدرسه"

    def test_decomposed_hamza_is_composed(self):
        decomposed = "أ"  # alef + combining hamza above
        assert normalize(decomposed).normalized == "أ"


class TestClusters:
    def test_marks_attach_to_their_letter(self):
        cs = split_clusters("كُتُبٌ")
        assert bare(cs) == "كتب"
        assert [len(c.marks) for c in cs] == [1, 1, 1]

    def test_mark_order_is_canonical(self):
        # shadda typed before fatha must equal fatha before shadda
        a = split_clusters("شَّ")
        b = split_clusters("شَّ")
        assert a == b

    def test_roundtrip(self):
        s = nfc("الشَّجَرَةُ")
        assert join_clusters(split_clusters(s)) == s

    def test_leading_mark_is_rejected(self):
        with pytest.raises(ValueError):
            split_clusters("َكتب")


class TestParseNoun:
    def test_article_and_case_ending_removed(self):
        p = parse_noun("الكِتَابُ")
        assert p.definite
        assert join_clusters(p.stem) == nfc("كِتَاب")
        assert p.original == "الكِتَابُ"

    def test_sun_letter_assimilation_shadda_removed(self):
        p = parse_noun("الشَّمْسُ")
        assert join_clusters(p.stem) == nfc("شَمْس")

    def test_tanween_alif_detected_both_spellings(self):
        assert parse_noun("كتابًا").tanween_alif
        assert parse_noun("كتاباً").tanween_alif
        assert not parse_noun("كتابا").tanween_alif

    def test_short_words_with_al_are_not_stripped(self):
        p = parse_noun("الم")  # ال + one letter is too short to be the article
        assert not p.definite

    @pytest.mark.parametrize("bad", ["", "كتاب جديد", "book", "ك"])
    def test_invalid(self, bad):
        with pytest.raises(InputError):
            parse_noun(bad)
