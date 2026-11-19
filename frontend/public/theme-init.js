// Applies the saved (or system) colour theme before the app renders, so the
// page never flashes the wrong theme. It is a separate file rather than an
// inline script because the Content-Security-Policy allows only 'self' scripts.
(function () {
  var theme = null;
  try {
    theme = localStorage.getItem("review-ai-theme");
  } catch {
    // Storage can be blocked by the browser; fall back to the system theme.
  }
  if (theme !== "light" && theme !== "dark") {
    theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", theme);
})();
