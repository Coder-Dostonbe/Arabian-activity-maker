"""Write the sample teacher files in desktop/samples/ (txt, xlsx, docx).

lugat.txt is a word list the way teachers type it: Arabic and Uzbek mixed in any order,
plurals and duals written beside the word. The import sorts it into word / translation rows.

Run: python desktop/scripts/make_samples.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sidecar"))
from office_writer import docx, xlsx  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "samples"

DUAL = [
    ["So'z", "Javob", "Izoh", "Variant 1", "Variant 2", "Variant 3"],
    ["كتاب", "كِتَابَانِ", "Ikkilik · Raf'", "كِتَابَيْنِ", "كِتَابَا", "كُتُبٌ"],
    ["شجرة", "شَجَرَتَانِ", "Ikkilik · Raf'", "شَجَرَتَيْنِ", "شَجَرَتَا", "أَشْجَارٌ"],
    ["عصا", "عَصَوَانِ", "Ikkilik · Raf'", "عَصَيَانِ", "عَصَوَيْنِ", "عِصِيٌّ"],
    ["مستشفى", "مُسْتَشْفَيَانِ", "Ikkilik · Raf'", "مُسْتَشْفَوَانِ", "مُسْتَشْفَيَيْنِ", "مُسْتَشْفَيَاتٌ"],
    ["قاض", "قَاضِيَانِ", "Ikkilik · Raf'", "قَاضَانِ", "قَاضِيَيْنِ", "قُضَاةٌ"],
]

TEST = [
    ["Savol", "Javob", "Variant 1", "Variant 2", "Variant 3"],
    ["«كتاب» so'zining ko'pligi qaysi?", "كُتُبٌ", "كِتَابَاتٌ", "كِتَابُونَ", "كِتَابَانِ"],
    ["«معلمة» so'zining ko'pligi qaysi?", "مُعَلِّمَاتٌ", "مُعَلِّمُونَ", "مَعَالِمُ", "مُعَلِّمَتَانِ"],
    ["في ... (المدرسة) — qaysi shakl to'g'ri?", "الْمَدْرَسَةِ", "الْمَدْرَسَةُ", "الْمَدْرَسَةَ", "مَدْرَسَةً"],
    ["«مهندس» — muzakkar solim ko'plik, raf'", "مُهَنْدِسُونَ", "مُهَنْدِسِينَ", "مُهَنْدِسَاتٌ", "مَهَانِدُ"],
]

VOCAB = """# ArabMorph AI — lug'at namunasi: arabcha va o'zbekcha aralash, ko'plik so'z yonida
كِتَابٌ ج كُتُبٌ – kitob
qalam – قَلَمٌ ج أَقْلَامٌ
بَيْتٌ (بُيُوتٌ) – uy
طَالِبٌ ج طُلَّابٌ | talaba | talabalar
عَيْنٌ مثنى عَيْنَانِ – ko'z
مَدْرَسَةٌ – maktab
o'qituvchi | مُعَلِّمٌ ج مُعَلِّمُونَ
"""


def main():
    OUT.mkdir(exist_ok=True)
    txt = "# ArabMorph AI — namuna fayl. Ustunlar: so'z | javob | izoh | noto'g'ri variantlar\n"
    txt += "\n".join(" | ".join(row) for row in DUAL) + "\n"
    (OUT / "namuna.txt").write_text(txt, encoding="utf-8")
    (OUT / "lugat.txt").write_text(VOCAB, encoding="utf-8")
    (OUT / "namuna.xlsx").write_bytes(xlsx({"Ikkilik": DUAL, "Test": TEST}))
    (OUT / "namuna.docx").write_bytes(docx(paragraphs=["ArabMorph AI — namuna"], tables=[TEST]))
    print(f"samples written to {OUT}")


if __name__ == "__main__":
    main()
