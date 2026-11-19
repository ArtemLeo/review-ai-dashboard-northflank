<template>
  <nav class="app-nav" aria-label="Main">
    <!-- aria-label keeps a name when the caption is hidden on phones. -->
    <button type="button" class="nav-item" aria-label="About Project" @click="emit('about')">
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
      <span class="item-label">About Project</span>
    </button>

    <span class="divider" aria-hidden="true"></span>

    <!-- Product mark centred in the navigation. -->
    <span class="brand" aria-hidden="true">
      <BrandLogo />
    </span>

    <span class="divider" aria-hidden="true"></span>

    <!-- A button, not a link: the browser shows no URL preview on hover. -->
    <button
      type="button"
      class="nav-item"
      :aria-label="target.label"
      @click="router.push(target.to)"
    >
      <span class="item-label">{{ target.label }}</span>
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <!-- A lock for the admin area, a door back to the home page. -->
        <template v-if="link === 'admin'">
          <rect x="4" y="11" width="16" height="10" rx="2" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </template>
        <template v-else>
          <path d="M3 21h18" />
          <path d="M6 21V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17" />
          <circle cx="14.5" cy="12" r="0.9" fill="currentColor" />
        </template>
      </svg>
    </button>
  </nav>
</template>

<script setup lang="ts">
/**
 * Top navigation of the public pages: one frosted capsule holding the
 * "About" dialog trigger, the product mark and a link to the other side of the app
 * (the home page or the admin area).
 */
import { computed } from "vue";
import { useRouter } from "vue-router";
import BrandLogo from "@/components/BrandLogo.vue";

const router = useRouter();

const props = defineProps<{
  /** The page the navigation link leads to. */
  link: "review" | "admin";
}>();

const emit = defineEmits<{
  /** Emitted when the "About" button is pressed. */
  about: [];
}>();

const target = computed(() =>
  props.link === "admin" ? { to: "/admin", label: "Admin Panel" } : { to: "/", label: "Home Page" }
);
</script>

<style scoped>
/* A floating glass capsule, in the spirit of the iOS frosted bars: a
   translucent dark fill, a strong backdrop blur and a hairline highlight. */
/* As wide as the card under it (480px, 400px on tablets), so the two read
   as one centred column. */
/* Two equal side columns keep the mark exactly in the middle, whatever the
   length of the link captions. */
.app-nav {
  display: grid;
  grid-template-columns: 1fr auto auto auto 1fr;
  align-items: center;
  gap: 0.35rem;
  width: 100%;
  max-width: 480px;
  padding: 0.55rem;
  border-radius: 999px;
  background: rgba(16, 21, 31, 0.5);
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow:
    0 18px 40px -16px rgba(0, 0, 0, 0.75),
    0 4px 12px -4px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

/* The product mark between the two links. */
.brand {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.7rem;
}

.brand-logo {
  width: 48px;
  height: 48px;
  filter: drop-shadow(0 3px 8px rgba(0, 0, 0, 0.55));
}

.divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.14);
}

.nav-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.7rem 0.6rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  /* Muted champagne gold: warm like the brand amber, but quieter than the
     primary buttons and clearly apart from the white brand label. */
  color: #f2d6a2;
  font-family: "Rajdhani", sans-serif;
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s ease;
  /* The same 3D lift as the brand label, so the labels stay legible over
     any part of the background photo. */
  text-shadow:
    0 1px 0 rgba(0, 0, 0, 0.55),
    0 2px 0 rgba(0, 0, 0, 0.35),
    0 4px 10px rgba(0, 0, 0, 0.6);
}

.nav-item:hover,
.nav-item:focus-visible {
  background: var(--ice-bg);
  color: var(--ice-text);
}

/* Keyboard focus adds a ring to the hover look, so it is easy to follow. */
.nav-item:focus-visible {
  outline: 2px solid var(--ice-text);
  outline-offset: 2px;
}

/* Icons get the matching shadow; text-shadow does not reach SVG strokes. */
.nav-item svg {
  transition: transform 0.2s ease;
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.55)) drop-shadow(0 3px 6px rgba(0, 0, 0, 0.55));
}

.nav-item:hover svg {
  transform: scale(1.12);
}

@media (max-width: 768px) {
  .app-nav {
    max-width: 400px;
  }
}

/* On phones the side items shrink to icons so the capsule fits one line. */
@media (max-width: 480px) {
  .brand {
    padding: 0.2rem 0.4rem;
  }

  .brand-logo {
    width: 40px;
    height: 40px;
  }

  .nav-item {
    padding: 0.55rem 0.65rem;
  }

  .item-label {
    display: none;
  }
}
</style>
