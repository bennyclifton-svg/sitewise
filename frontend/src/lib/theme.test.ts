import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  applyTheme,
  readStoredTheme,
  setTheme,
  subscribeTheme,
  THEME_STORAGE_KEY,
  toggleTheme,
} from "@/lib/theme";

describe("color theme", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
  });

  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
  });

  it("defaults to dark when nothing is stored", () => {
    expect(readStoredTheme()).toBe("dark");
  });

  it("reads a stored light theme", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    expect(readStoredTheme()).toBe("light");
  });

  it("ignores an unknown stored value", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");
    expect(readStoredTheme()).toBe("dark");
  });

  it("applies the theme to the document root", () => {
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });

  it("persists the theme and applies it", () => {
    setTheme("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("toggles from dark to light and back", () => {
    expect(toggleTheme()).toBe("light");
    expect(readStoredTheme()).toBe("light");
    expect(toggleTheme()).toBe("dark");
    expect(readStoredTheme()).toBe("dark");
  });

  it("notifies subscribers when the theme changes", () => {
    let calls = 0;
    const stop = subscribeTheme(() => {
      calls += 1;
    });
    setTheme("light");
    stop();
    setTheme("dark");
    expect(calls).toBe(1);
  });
});
