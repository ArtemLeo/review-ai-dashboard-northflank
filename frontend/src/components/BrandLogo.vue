<template>
  <!-- The 2-unit margin keeps the anti-aliased rim of the disc inside the canvas. -->
  <svg class="brand-logo" viewBox="-2 -2 104 104" aria-hidden="true">
    <defs>
      <radialGradient :id="fillId" cx="50%" cy="85%" r="85%">
        <stop offset="0%" stop-color="#a7fbe9" />
        <stop offset="100%" stop-color="#5ef2d4" />
      </radialGradient>
    </defs>
    <circle cx="50" cy="50" r="50" :fill="`url(#${fillId})`" />
    <text
      x="50"
      y="51"
      fill="#000"
      font-family="Rajdhani, sans-serif"
      font-size="39"
      font-weight="700"
      letter-spacing="-1"
      text-anchor="middle"
      dominant-baseline="middle"
    >
      CS2
    </text>
  </svg>
</template>

<script setup lang="ts">
/**
 * The product logo: a mint disc with a black "CS2". The size comes from the
 * parent through CSS (width and height of `.brand-logo`).
 */
import { useId } from "vue";

/** Unique gradient id, so two logos on one page never share a definition. */
const fillId = `brand-logo-fill-${useId()}`;
</script>

<style scoped>
/* A dark contact edge and a soft drop lift the disc off its background,
   the mint glow keeps it tied to its own colour. */
.brand-logo {
  flex-shrink: 0;
  overflow: visible;
  filter: drop-shadow(0 2px 0 rgba(0, 0, 0, 0.45)) drop-shadow(0 4px 8px rgba(0, 0, 0, 0.55))
    drop-shadow(0 0 8px rgba(94, 242, 212, 0.35));
}
</style>
