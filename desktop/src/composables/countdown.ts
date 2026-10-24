import { onBeforeUnmount, ref } from "vue";

/**
 * A pausable countdown measured against the clock, so it does not drift when
 * the window is busy. `onDone` runs once when the time reaches zero.
 */
export function useCountdown() {
  const remaining = ref(0);
  const total = ref(0);
  const running = ref(false);
  let deadline = 0;
  let handle: number | undefined;
  let onDone: (() => void) | null = null;

  function clear() {
    if (handle !== undefined) window.clearInterval(handle);
    handle = undefined;
  }

  function tick() {
    remaining.value = Math.max(0, deadline - performance.now());
    if (remaining.value === 0) {
      clear();
      running.value = false;
      const done = onDone;
      onDone = null;
      done?.();
    }
  }

  function resume() {
    if (running.value || !onDone) return;
    deadline = performance.now() + remaining.value;
    running.value = true;
    handle = window.setInterval(tick, 100);
  }

  function start(ms: number, done: () => void) {
    stop();
    total.value = remaining.value = ms;
    onDone = done;
    resume();
  }

  function pause() {
    if (!running.value) return;
    clear();
    remaining.value = Math.max(0, deadline - performance.now());
    running.value = false;
  }

  function stop() {
    clear();
    running.value = false;
    onDone = null;
  }

  onBeforeUnmount(stop);
  return { remaining, total, running, start, pause, resume, stop };
}
