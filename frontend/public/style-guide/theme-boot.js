/* Apply the stored colour theme before first paint. Keep in lockstep with
   frontend/src/lib/theme.ts — storage key clerk.colorTheme.v1. */
(function () {
  var key = "clerk.colorTheme.v1";
  var theme = "dark";
  try {
    var stored = window.localStorage.getItem(key);
    if (stored === "light" || stored === "dark") theme = stored;
  } catch (error) {
    /* private mode / blocked storage — stay on dark */
  }
  var root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
  var colorScheme = document.querySelector('meta[name="color-scheme"]');
  if (colorScheme) colorScheme.setAttribute("content", theme);
  var themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) {
    themeColor.setAttribute("content", theme === "light" ? "#F7F7F4" : "#060608");
  }
})();
