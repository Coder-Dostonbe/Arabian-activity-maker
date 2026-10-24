"""Write the sample teacher files in desktop/samples/ (txt, xlsx, docx).

Run: python desktop/scripts/make_samples.py
"""

from pathlib import Path

from office_writer import docx, xlsx

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


def main():
    OUT.mkdir(exist_ok=True)
    txt = "# ArabMorph AI — namuna fayl. Ustunlar: so'z | javob | izoh | noto'g'ri variantlar\n"
    txt += "\n".join(" | ".join(row) for row in DUAL) + "\n"
    (OUT / "namuna.txt").write_text(txt, encoding="utf-8")
    (OUT / "namuna.xlsx").write_bytes(xlsx({"Ikkilik": DUAL, "Test": TEST}))
    (OUT / "namuna.docx").write_bytes(docx(paragraphs=["ArabMorph AI — namuna"], tables=[TEST]))
    print(f"samples written to {OUT}")


if __name__ == "__main__":
    main()
