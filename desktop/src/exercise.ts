// What the class sees and what counts as the answer, for activity cards and test questions.
import type { Item } from "./stores/sets";
import { shuffle } from "./util";

/** Activity direction: show the Arabic word and ask its Uzbek meaning, the reverse, or the row's own answer. */
export type Direction = "ar_uz" | "uz_ar" | "word_answer";
export const directions: Direction[] = ["ar_uz", "uz_ar", "word_answer"];

export interface Card {
  item: Item;
  front: string;
  back: string;
}

/** The card for `item` in `dir`, or null when the item has nothing to show that way (no translation). */
export function card(item: Item, dir: Direction): Card | null {
  if (dir === "word_answer") return { item, front: item.prompt, back: item.answer };
  if (!item.prompt || !item.translation) return null;
  return dir === "ar_uz"
    ? { item, front: item.prompt, back: item.translation }
    : { item, front: item.translation, back: item.prompt };
}

export function cards(items: Item[], dir: Direction): Card[] {
  return items.map((i) => card(i, dir)).filter((c): c is Card => c !== null);
}

// --- test questions -------------------------------------------------------------

export type Ask = "plural" | "dual" | "answer" | "translation";

export interface Question {
  item: Item;
  ask: Ask;
  shown: string;
  answer: string;
  options: string[] | null;
}

// The test always asks in Uzbek, whatever the interface language: the translations it asks for are Uzbek.
export const UZ_QUESTIONS: Record<Ask, string> = {
  plural: "Bu so'zning ko'pligi qanday?",
  dual: "Bu so'zning ikkiligi qanday?",
  translation: "Bu so'z o'zbekchada nima degani?",
  answer: "To'g'ri javobni toping",
};

/** A plural / dual asks for that form of its word, a row with an answer asks for it, a word asks its meaning. */
function ask(item: Item): Omit<Question, "options"> | null {
  if (item.form && item.base && item.prompt) return { item, ask: item.form, shown: item.base, answer: item.prompt };
  if (item.answer) return { item, ask: "answer", shown: item.prompt, answer: item.answer };
  if (item.translation) return { item, ask: "translation", shown: item.prompt, answer: item.translation };
  return null;
}

export function askable(items: Item[]): Item[] {
  return items.filter((i) => ask(i) !== null);
}

/** Questions in order; options are the row's own wrong answers, else answers of the same kind of question. */
export function questions(items: Item[], withOptions: boolean): Question[] {
  const asked = items.map(ask).filter((q): q is Omit<Question, "options"> => q !== null);
  return asked.map((q) => {
    if (!withOptions) return { ...q, options: null };
    let wrong = q.ask === "answer" ? q.item.options.filter((o) => o !== q.answer) : [];
    if (!wrong.length) {
      const others = [...new Set(asked.filter((o) => o.ask === q.ask).map((o) => o.answer))];
      wrong = shuffle(others.filter((a) => a && a !== q.answer));
    }
    wrong = wrong.slice(0, 3);
    return { ...q, options: wrong.length ? shuffle([q.answer, ...wrong]) : null };
  });
}
