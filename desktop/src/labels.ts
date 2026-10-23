// Uzbek interface labels. Arabic grammatical terms are kept alongside.
import type { CaseName, NumberName, PluralKind, StateName, Status } from "./engine";

export const numberLabel: Record<NumberName, string> = {
  singular: "Birlik (مفرد)",
  dual: "Ikkilik (مثنى)",
  plural: "Ko'plik (جمع)",
};

export const caseLabel: Record<CaseName, string> = {
  nominative: "Raf' (رفع)",
  accusative: "Nasb (نصب)",
  genitive: "Jarr (جر)",
};

export const stateLabel: Record<StateName, string> = {
  indefinite: "Noaniq (نكرة)",
  definite: "Aniq — ال (معرفة)",
  construct: "Izofa (مضاف)",
};

export const kindLabel: Record<PluralKind, string> = {
  broken: "Siniq ko'plik (تكسير)",
  sound_masculine: "Muzakkar solim (ـون)",
  sound_feminine: "Muannas solim (ـات)",
};

export const statusLabel: Record<Status, string> = {
  ok: "Aniqlandi",
  ambiguous: "Bir nechta o'qilish",
  error: "Yasab bo'lmadi",
};

export const sourceLabel: Record<string, string> = {
  rule: "Qoida",
  lexicon: "Lug'at",
  heuristic: "Imlo taxmini",
  asserted: "Siz ko'rsatgan tur",
};

export const sourceHint: Record<string, string> = {
  rule: "Imlo va diakritikadan aniq qoida bilan chiqarildi",
  lexicon: "Lug'at yozuvi hal qiluvchi ma'lumotni berdi",
  heuristic: "Imlo odatiga asoslangan taxmin — xato bo'lishi mumkin",
  asserted: "Ko'plik turini siz ko'rsatdingiz; dvigatel buni tekshira olmaydi",
};

export const finalClassLabel: Record<string, string> = {
  sound: "Sog'lom (صحيح)",
  maqsur: "Maqsur (مقصور)",
  manqus: "Manqus (منقوص)",
  mamdud: "Mamdud (ممدود)",
};

export const posLabel: Record<string, string> = {
  noun: "Ot (اسم)",
  adjective: "Sifat (صفة)",
  proper_noun: "Atoqli ot (علم)",
};

export const genderLabel: Record<string, string> = {
  masculine: "Muzakkar",
  feminine: "Muannas",
  unknown: "—",
};
