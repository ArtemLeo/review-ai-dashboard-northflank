/**
 * Light/dark theme management.
 *
 * The theme the user picks is kept in localStorage; until then the system
 * preference applies.  The active theme is reflected as a `data-theme`
 * attribute (`"light"` | `"dark"`) on the `<html>` element so every
 * component can scope its colours to the current theme.  public/theme-init.js
 * sets the attribute before the first render, so nothing is written until the
 * user actually switches the theme.
 */

import { ref } from "vue";
import type { Ref } from "vue";

const THEME_KEY = "review-ai-theme";

type Theme = "light" | "dark";

/**
 * Reads the saved theme. Storage can be blocked by the browser (e.g. private
 * mode or disabled site data); the app must still start, so null is returned.
 */
function readSavedTheme(): string | null {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

const savedTheme = readSavedTheme();
// An unknown saved value counts as no choice, exactly as in theme-init.js,
// so the toggle shows the theme the page actually has.
const darkTheme = ref<boolean>(
  savedTheme === "dark" ||
    (savedTheme !== "light" &&
      (window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false))
);

function applyTheme(theme: Theme): void {
  const dark = theme === "dark";
  darkTheme.value = dark;
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // The choice simply is not remembered when storage is blocked.
  }
}

/** Toggle between light and dark themes. */
function toggleTheme(): void {
  const next = darkTheme.value ? "light" : "dark";
  applyTheme(next);
}

export function useTheme(): { darkTheme: Ref<boolean>; toggleTheme: () => void } {
  return { darkTheme, toggleTheme };
}
