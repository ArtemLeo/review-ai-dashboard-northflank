<template>
  <router-view />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* "Ice" hover palette: a cool, slightly blue glow for every quiet
   (outlined or transparent) control, next to the amber primary buttons. */
:root {
  --ice-text: #bae6fd;
  --ice-bg: rgba(125, 211, 252, 0.14);
  --ice-border: rgba(125, 211, 252, 0.4);
  --ice-glow: rgba(56, 189, 248, 0.25);
}

body {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  /* Dark base so the app never flashes white before a view is mounted. */
  background-color: #0d111b;
}

#app {
  min-height: 100vh;
}

/* Slim, dark scrollbars to match the interface. */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.16) transparent;
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.14);
  border: 2px solid transparent;
  background-clip: content-box;
  border-radius: 6px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.26);
  background-clip: content-box;
}

/* Respect the system setting for less motion: transitions and animations
   finish at once, so nothing slides, pulses or nudges. */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
