import { ref, watch, type Ref } from "vue";
import { getSetting, setSetting } from "./storage";

export function newId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function shuffle<T>(items: readonly T[]): T[] {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

const ARABIC = /[ء-يٱ-ۓݐ-ݿ]/g;
const OTHER_LETTERS = /[A-Za-zÀ-ɏЀ-ӿ]/g;

/** "ar" (Arabic font, RTL) for text that is mostly Arabic, so mixed notes like "Ikkilik (مثنى)" stay LTR. */
export function arClass(text: string | null | undefined): string {
  if (!text) return "";
  const arabic = text.match(ARABIC)?.length ?? 0;
  return arabic > 0 && arabic >= (text.match(OTHER_LETTERS)?.length ?? 0) ? "ar" : "";
}

/** "m:ss" for a remaining time in milliseconds, rounded up to the next second. */
export function formatClock(ms: number): string {
  const total = Math.ceil(Math.max(0, ms) / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

// Settings live in the app's settings file (see storage.ts), loaded before the UI starts.
export function readStorage<T>(key: string, fallback: T): T {
  return getSetting(key, fallback);
}

export function writeStorage(key: string, value: unknown) {
  setSetting(key, value);
}

/** A ref that remembers its value between runs (per-user preference). */
export function persisted<T>(key: string, initial: T): Ref<T> {
  const r = ref(readStorage(key, initial)) as Ref<T>;
  watch(r, (v) => writeStorage(key, v), { deep: true });
  return r;
}

/** Short tone for "time is up"; silently does nothing where audio is unavailable. */
export function beep() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.9);
    osc.connect(gain).connect(ctx.destination);
    osc.onended = () => void ctx.close();
    osc.start();
    osc.stop(ctx.currentTime + 0.9);
  } catch {
    /* no audio device */
  }
}

/** File bytes as base64, for the engine service. */
export async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

/** Text direction matching `arClass`: RTL only for mostly-Arabic text. */
export function textDir(text: string | null | undefined): "rtl" | "ltr" {
  return arClass(text) ? "rtl" : "ltr";
}
