// Saved data is loaded before any module that reads a setting is evaluated.
import { initStorage } from "./storage";

void initStorage().finally(async () => (await import("./app")).start());
