const STORAGE_KEY = "clerk-theme";

export type ThemeMode = "light" | "dark";

export function readThemeMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "dark" ? "dark" : "light";
}

export function isDarkMode(): boolean {
  return document.documentElement.classList.contains("dark");
}

export function applyThemeMode(mode: ThemeMode): void {
  document.documentElement.classList.toggle("dark", mode === "dark");
  localStorage.setItem(STORAGE_KEY, mode);
}

export function initTheme(): void {
  applyThemeMode(readThemeMode());
}

export function toggleThemeMode(): ThemeMode {
  const next: ThemeMode = isDarkMode() ? "light" : "dark";
  applyThemeMode(next);
  return next;
}
