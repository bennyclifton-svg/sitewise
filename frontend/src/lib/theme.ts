export type ColorTheme = "dark" | "light";

export const THEME_STORAGE_KEY = "clerk.colorTheme.v1";
export const THEME_CHANGE_EVENT = "clerk:color-theme-change";

export const THEME_VOID_HEX = {
  dark: "#060608",
  light: "#F7F7F4",
} as const;

export function isColorTheme(value: unknown): value is ColorTheme {
  return value === "dark" || value === "light";
}

export function readStoredTheme(): ColorTheme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return isColorTheme(stored) ? stored : "dark";
}

export function applyTheme(
  theme: ColorTheme,
  root: HTMLElement = document.documentElement,
): void {
  root.dataset.theme = theme;
  root.style.colorScheme = theme;

  const colorScheme = document.querySelector('meta[name="color-scheme"]');
  colorScheme?.setAttribute("content", theme);

  const themeColor = document.querySelector('meta[name="theme-color"]');
  themeColor?.setAttribute("content", THEME_VOID_HEX[theme]);
}

export function setTheme(theme: ColorTheme): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  applyTheme(theme);
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

export function toggleTheme(): ColorTheme {
  const next = readStoredTheme() === "light" ? "dark" : "light";
  setTheme(next);
  return next;
}

export function subscribeTheme(onStoreChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === THEME_STORAGE_KEY || event.key === null) {
      applyTheme(readStoredTheme());
      onStoreChange();
    }
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(THEME_CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(THEME_CHANGE_EVENT, onStoreChange);
  };
}
