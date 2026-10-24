// Optional online assistant: drafts activity items with Claude using the teacher's own API key.
// Nothing here runs unless the teacher asks for it; the offline engine needs no network.
import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-opus-5-5";
export const MAX_DRAFT_ITEMS = 40;

export interface DraftItem {
  prompt: string;
  answer: string;
  note: string;
  options: string[];
}

export type ClaudeErrorKind = "auth" | "rate" | "network" | "refusal" | "invalid" | "other";

export class ClaudeError extends Error {
  constructor(public kind: ClaudeErrorKind, message = "") {
    super(message);
  }
}

const SCHEMA = {
  type: "object",
  properties: {
    items: {
      type: "array",
      items: {
        type: "object",
        properties: {
          prompt: { type: "string" },
          answer: { type: "string" },
          note: { type: "string" },
          options: { type: "array", items: { type: "string" } },
        },
        required: ["prompt", "answer", "note", "options"],
        additionalProperties: false,
      },
    },
  },
  required: ["items"],
  additionalProperties: false,
};

const SYSTEM = `You write classroom exercise items for students learning Arabic morphology and grammar \
(singular, dual and plural forms, case endings, the definite article, iḍāfa).

Each item is shown to the whole class on a screen:
- prompt: the Arabic word or a short question.
- answer: the single correct answer. Write Arabic with full diacritics.
- note: a short hint in the requested interface language, e.g. which form is asked for.
- options: three wrong answers a student could plausibly confuse with the correct one, such as the same word \
in another case or number. Never repeat the correct answer among them.

Correctness matters more than variety: leave out any item whose answer you are not certain of, \
and avoid words whose form depends on a meaning the prompt does not state.`;

function clean(value: unknown, max = 300): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, max) : "";
}

export async function draftItems(apiKey: string, topic: string, count: number, language: string): Promise<DraftItem[]> {
  const client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true, maxRetries: 1 });
  let response: Anthropic.Beta.BetaMessage;
  try {
    response = await client.beta.messages.create({
      model: MODEL,
      max_tokens: 16000,
      // Opt in to server-side fallback: if a safety classifier declines, the API retries on its recommended model.
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      output_config: { effort: "medium", format: { type: "json_schema", schema: SCHEMA } },
      system: SYSTEM,
      messages: [
        {
          role: "user",
          content: `Topic: ${topic}\nNumber of items: ${count}\nInterface language for prompts and notes: ${language}`,
        },
      ],
    });
  } catch (e) {
    if (e instanceof Anthropic.AuthenticationError || e instanceof Anthropic.PermissionDeniedError) {
      throw new ClaudeError("auth");
    }
    if (e instanceof Anthropic.RateLimitError) throw new ClaudeError("rate");
    if (e instanceof Anthropic.APIConnectionError) throw new ClaudeError("network");
    if (e instanceof Anthropic.APIError) throw new ClaudeError("other", e.message);
    throw e;
  }

  if (response.stop_reason === "refusal") throw new ClaudeError("refusal");
  const text = response.content.find((b): b is Anthropic.Beta.BetaTextBlock => b.type === "text")?.text;
  let parsed: unknown;
  try {
    parsed = JSON.parse(text ?? "");
  } catch {
    throw new ClaudeError("invalid");
  }
  const raw = (parsed as { items?: unknown }).items;
  if (!Array.isArray(raw)) throw new ClaudeError("invalid");

  const items: DraftItem[] = [];
  for (const r of raw.slice(0, MAX_DRAFT_ITEMS)) {
    const prompt = clean(r?.prompt);
    const answer = clean(r?.answer);
    if (!prompt || !answer) continue;
    const options = Array.isArray(r?.options)
      ? [...new Set(r.options.map((o: unknown) => clean(o)))].filter((o): o is string => !!o && o !== answer).slice(0, 6)
      : [];
    items.push({ prompt, answer, note: clean(r?.note), options });
  }
  if (!items.length) throw new ClaudeError("invalid");
  return items;
}
