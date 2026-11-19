<template>
  <header class="header">
    <div class="header-title">
      <h1>
        <BrandLogo />
        Admin Dashboard
      </h1>
      <span class="system-status">
        <span class="status-dot"></span>
        System Online
      </span>
    </div>
    <div class="header-actions">
      <nav class="header-links" aria-label="Pages">
        <button type="button" class="header-link" aria-label="About Project" @click="emit('about')">
          <svg
            width="16"
            height="16"
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
          <span class="link-label">About Project</span>
        </button>
        <!-- A button, not a link: the browser shows no URL preview on hover. -->
        <button type="button" class="header-link" aria-label="Home Page" @click="router.push('/')">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <!-- The same door as on the public navigation bar. -->
            <path d="M3 21h18" />
            <path d="M6 21V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17" />
            <circle cx="14.5" cy="12" r="0.9" fill="currentColor" />
          </svg>
          <span class="link-label">Home Page</span>
        </button>
      </nav>
      <span class="header-divider" aria-hidden="true"></span>
      <div class="theme-switch" role="group" aria-label="Theme">
        <button
          type="button"
          class="theme-option"
          :class="{ active: !isDark }"
          :aria-pressed="!isDark"
          aria-label="Light theme"
          @click="isDark && emit('toggle-theme')"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="4" />
            <path
              d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
            />
          </svg>
        </button>
        <button
          type="button"
          class="theme-option"
          :class="{ active: isDark }"
          :aria-pressed="isDark"
          aria-label="Dark theme"
          @click="!isDark && emit('toggle-theme')"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        </button>
      </div>

      <span class="header-divider" aria-hidden="true"></span>

      <button class="logout-btn" @click="emit('logout')">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
        Logout
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * Top bar of the admin area: the title and system status, the About and
 * Home Page links, the theme switch and logout.
 */
import { useRouter } from "vue-router";
import BrandLogo from "@/components/BrandLogo.vue";

const router = useRouter();

defineProps<{
  /** Whether the dark theme is active. */
  isDark: boolean;
}>();

const emit = defineEmits<{
  /** Emitted when the theme switch is pressed. */
  "toggle-theme": [];
  /** Emitted when the logout button is pressed. */
  logout: [];
  /** Emitted when the "About" button is pressed. */
  about: [];
}>();
</script>

<style scoped>
/* The header and the toolbar are two stacked layers of the same dark
   family. Each one is a frosted panel with three stacked shadows — a
   wide ambient shadow, a tighter contact shadow and a hairline inner
   highlight on top — so they read as raised surfaces instead of flat
   bands of colour. */
.header {
  position: relative;
  background: linear-gradient(180deg, rgba(24, 30, 43, 0.92) 0%, rgba(16, 21, 31, 0.88) 100%);
  backdrop-filter: blur(14px) saturate(120%);
  -webkit-backdrop-filter: blur(14px) saturate(120%);
  padding: 1.875rem 2rem;
  min-height: 132px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 0 0 auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 18px 34px -18px rgba(0, 0, 0, 0.72),
    0 6px 14px -8px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* The actions are three groups by purpose — page navigation, display
   settings, then the session exit at the far right — split by hairline
   dividers so they never read as one cluster. */
.header-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.12);
}

/* Navigation links share one recessed track, the same shape as the theme
   switch, so the pair reads as a single group of quiet links. */
.header-links {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: rgba(8, 11, 17, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.45);
}

.header-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  height: 32px;
  padding: 0 0.95rem;
  background: transparent;
  border: none;
  border-radius: 999px;
  color: #94a3b8;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.header-link:hover,
.header-link:focus-visible {
  outline: none;
  /* The cool "ice" glow: navigation stays calm next to the amber controls. */
  color: var(--ice-text);
  background: var(--ice-bg);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

/* Narrow screens keep both links, as icons only. */
@media (max-width: 900px) {
  .link-label {
    display: none;
  }

  .header-link {
    padding: 0 0.7rem;
  }
}

/* Segmented sun / moon switch, the same pattern as the UA / EN switch of
   the About dialog: a recessed track with the active option filled amber. */
.theme-switch {
  display: inline-flex;
  padding: 3px;
  background: rgba(8, 11, 17, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.45);
}

.theme-option {
  width: 40px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-option:hover:not(.active) {
  color: var(--ice-text);
}

.theme-option.active {
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  color: #1c1305;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
  cursor: default;
}

/* The logout button keeps its own red family: it ends the session, so it
   stands apart from the display settings, past the last divider. */
.logout-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 1.6rem;
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.22) 0%, rgba(239, 68, 68, 0.12) 100%);
  color: #fecaca;
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: 6px;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
  cursor: pointer;
  font-family: "Rajdhani", sans-serif;
  font-weight: 700;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  transition: all 0.2s ease;
  white-space: nowrap;
}

/* Solid amber seam under the header — one uniform Counter-Strike amber
   colour across the entire line, no fading. */
.header::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background-color: #f59e0b;
  pointer-events: none;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header h1 {
  margin: 0;
  font-family: "Rajdhani", sans-serif;
  font-size: 2.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: #f8fafc;
  padding: 0.3rem 0;
  text-shadow: 0 2px 14px rgba(245, 158, 11, 0.22);
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

/* The logo matches the height of the capital letters' line box. */
.header h1 .brand-logo {
  width: 2.6rem;
  height: 2.6rem;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.28);
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.18);
  animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

.logout-btn:hover {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.34) 0%, rgba(239, 68, 68, 0.2) 100%);
  color: #fee2e2;
  transform: translateY(-1px);
  box-shadow:
    0 8px 18px -4px rgba(239, 68, 68, 0.3),
    0 2px 6px -1px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* Tablets: the controls move under the title when the two do not fit side
   by side, instead of pushing the logout button off the screen. */
@media (max-width: 1000px) {
  .header {
    flex-wrap: wrap;
    row-gap: 1rem;
  }
}

/* Phones: the title and the controls stack in two rows that both fit the
   screen, so the header never widens the page. */
@media (max-width: 640px) {
  .header {
    flex-wrap: wrap;
    gap: 1rem;
    min-height: 0;
    padding: 1.25rem 1rem;
  }

  .header-title {
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .header h1 {
    font-size: 1.6rem;
    letter-spacing: 2px;
    gap: 0.6rem;
  }

  .header h1 .brand-logo {
    width: 1.7rem;
    height: 1.7rem;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 1rem;
    row-gap: 0.75rem;
  }

  .logout-btn {
    padding: 0.6rem 1.1rem;
  }

  /* The links, the theme switch and logout share one row on a phone;
     spacing alone separates them there. */
  .header-divider {
    display: none;
  }
}
</style>
