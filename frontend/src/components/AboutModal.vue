<template>
  <BaseModal
    :open="open"
    :title="t.title"
    :subtitle="t.subtitle"
    modal-class="about-modal"
    :lang="locale"
    :close-label="t.closeLabel"
    @close="emit('close')"
  >
    <template #actions>
      <div class="lang-switch" role="group" :aria-label="t.languageLabel">
        <button
          v-for="option in LOCALES"
          :key="option"
          type="button"
          class="lang-option"
          :class="{ active: locale === option }"
          :aria-pressed="locale === option"
          @click="setLocale(option)"
        >
          {{ option === "uk" ? "UA" : "EN" }}
        </button>
      </div>
    </template>

    <p class="lead">{{ t.lead }}</p>

    <section>
      <h3 class="section-title">{{ t.problemTitle }}</h3>
      <ul class="problems">
        <li v-for="problem in t.problems" :key="problem.title" class="problem">
          <div class="step-head">
            <span class="step-number problem-icon" aria-hidden="true">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.25"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path v-for="d in FEATURE_ICONS[problem.icon]" :key="d" :d="d" />
              </svg>
            </span>
            <h4>{{ problem.title }}</h4>
          </div>
          <p>{{ problem.text }}</p>
        </li>
      </ul>
    </section>

    <section>
      <h3 class="section-title">{{ t.featuresTitle }}</h3>
      <div class="features">
        <div v-for="feature in t.features" :key="feature.title" class="feature">
          <div class="step-head">
            <span class="step-number feature-icon" aria-hidden="true">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.25"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path v-for="d in FEATURE_ICONS[feature.icon]" :key="d" :d="d" />
              </svg>
            </span>
            <h4>{{ feature.title }}</h4>
          </div>
          <p>{{ feature.text }}</p>
        </div>
      </div>
    </section>

    <section>
      <h3 class="section-title">{{ t.stepsTitle }}</h3>
      <ol class="steps">
        <li v-for="(step, index) in t.steps" :key="step.title" class="step">
          <div class="step-head">
            <span class="step-number solution-number">{{ index + 1 }}</span>
            <h4>{{ step.title }}</h4>
          </div>
          <p>{{ step.text }}</p>
        </li>
      </ol>
    </section>

    <section>
      <h3 class="section-title">{{ t.businessTitle }}</h3>
      <ul class="business">
        <li v-for="point in t.business" :key="point">{{ point }}</li>
      </ul>
    </section>

    <section>
      <h3 class="section-title">{{ t.stackTitle }}</h3>
      <div class="stack">
        <span v-for="tech in ABOUT_STACK" :key="tech" class="badge tech">{{ tech }}</span>
      </div>
    </section>

    <!-- Shown only while part of the content is still below the fold. -->
    <div class="scroll-hint-anchor">
      <Transition name="hint">
        <div v-if="moreBelow" class="scroll-hint">
          <button
            type="button"
            class="scroll-hint-btn"
            :aria-label="t.scrollLabel"
            @click="scrollDown"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        </div>
      </Transition>
    </div>
    <div ref="contentEnd" aria-hidden="true"></div>
  </BaseModal>
</template>

<script setup lang="ts">
/** Product overview dialog shared by the public pages and the dashboard. */
import { computed, ref, watch } from "vue";
import BaseModal from "@/components/admin/BaseModal.vue";
import {
  ABOUT_CONTENT,
  ABOUT_STACK,
  FEATURE_ICONS,
  type AboutLocale,
} from "@/components/aboutContent";
import { keepFocusInDialog } from "@/utils/modalStack";

defineProps<{
  /** Whether the dialog is visible. */
  open: boolean;
}>();

const emit = defineEmits<{
  /** Emitted when the dialog should be dismissed. */
  close: [];
}>();

/** Ukrainian comes first; the choice is remembered in the browser. */
const LOCALES: AboutLocale[] = ["uk", "en"];
const LOCALE_KEY = "about-dialog-locale";

function readLocale(): AboutLocale {
  try {
    return localStorage.getItem(LOCALE_KEY) === "en" ? "en" : "uk";
  } catch {
    return "uk";
  }
}

const locale = ref<AboutLocale>(readLocale());
const t = computed(() => ABOUT_CONTENT[locale.value]);

function setLocale(value: AboutLocale): void {
  locale.value = value;
  try {
    localStorage.setItem(LOCALE_KEY, value);
  } catch {
    // Storage may be blocked (private mode); the choice lasts for this page only.
  }
}

/** Marker after the last section; while it is hidden, more content is below. */
const contentEnd = ref<HTMLElement | null>(null);
const moreBelow = ref(false);

// The content mounts each time the dialog opens, so the observer follows the marker.
watch(contentEnd, (element, _previous, onCleanup) => {
  moreBelow.value = false;
  if (!element || typeof IntersectionObserver === "undefined") return;
  const observer = new IntersectionObserver(([entry]) => {
    moreBelow.value = !entry.isIntersecting;
  });
  observer.observe(element);
  onCleanup(() => observer.disconnect());
});

/** The hint hides once the end is in view, so its focus goes to the dialog first. */
function scrollDown(event: MouseEvent): void {
  keepFocusInDialog(event.currentTarget);
  // People who asked the system for less motion get a jump, not an animation.
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  contentEnd.value?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "end" });
}
</script>

<style scoped>
/* A wide panel lets every section fit on one laptop screen without scrolling.
   The selector out-weighs the default width set inside BaseModal. */
:global(.modal-overlay .modal.about-modal) {
  /* One source for the panel padding; the scroll hint bleeds over it. */
  --about-pad-y: 1.75rem;
  --about-pad-x: 2rem;
  max-width: 1040px;
  max-height: 92vh;
  padding: var(--about-pad-y) var(--about-pad-x);
}

/* Rajdhani has no Cyrillic, so the heading switches to Exo 2, which covers
   both languages and keeps the same technical look. */
:global(.modal-overlay .about-modal .modal-title) {
  font-family: "Exo 2", "Rajdhani", sans-serif;
  font-size: 1.75rem;
  letter-spacing: 1.5px;
}

/* Segmented UA / EN switch in the same amber family as the buttons. */
.lang-switch {
  display: inline-flex;
  padding: 3px;
  background: rgba(8, 11, 17, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.45);
}

.lang-option {
  padding: 0.3rem 0.85rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #94a3b8;
  font-family: "Exo 2", "Rajdhani", sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 1.2px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.lang-option:hover:not(.active) {
  color: var(--ice-text);
}

.lang-option.active {
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  color: #1c1305;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

/* Business points: short lines with amber markers. */
.business {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.business li {
  position: relative;
  padding-left: 1.1rem;
  color: #cbd5e1;
  line-height: 1.55;
  font-size: 0.92rem;
}

.business li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.6em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.6);
}

.lead {
  color: #cbd5e1;
  line-height: 1.6;
  font-size: 0.98rem;
}

/* Each section is a raised panel, a step lighter than the dialog, so it is
   clear where one block ends and the next begins. The inner cards stay
   darker, which reads as a recess inside the panel. */
section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem 1.1rem 1.1rem;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.045) 0%,
    rgba(255, 255, 255, 0.02) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  box-shadow:
    0 10px 24px -14px rgba(0, 0, 0, 0.8),
    0 3px 8px -4px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.section-title {
  font-family: "Exo 2", "Rajdhani", sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #f59e0b;
}

h4 {
  font-family: "Exo 2", "Rajdhani", sans-serif;
  font-size: 1rem;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 0.15rem;
}

p,
li {
  color: #94a3b8;
  font-size: 0.875rem;
  line-height: 1.5;
}

/* The three pains sit side by side, each with a red accent edge. */
.problems {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

/* Pain cards reuse the step layout with a red "danger" disc instead of the
   amber one. */
.problem-icon {
  background: linear-gradient(180deg, #f87171 0%, #ef4444 58%, #c62828 100%);
  color: #2a0909;
}

.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.problem,
.feature,
.step {
  display: flex;
  gap: 0.75rem;
  padding: 0.85rem;
  background: rgba(8, 11, 17, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.steps {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

/* Feature cards share the step layout: an amber disc with the icon and the
   name on one line, the description below. */
.problem,
.feature,
.step {
  flex-direction: column;
  gap: 0.35rem;
}

/* The number and the step name share one line. */
.step-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.step-head h4 {
  margin-bottom: 0;
}

.step-number {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  color: #1c1305;
  font-family: "Exo 2", "Rajdhani", sans-serif;
  font-weight: 700;
}

.stack {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* Traffic-light sections: red problems, amber features, green steps; the
   stack badges take the blue of code editors. */
.solution-number {
  background: linear-gradient(180deg, #4ade80 0%, #22c55e 58%, #15803d 100%);
  color: #052e16;
}

.badge.tech {
  background: rgba(0, 122, 204, 0.14);
  color: #7cc4fa;
  border: 1px solid rgba(0, 122, 204, 0.45);
}

/* A zero-height sticky anchor keeps the hint glued to the bottom edge of
   the scrolling panel without taking any room in the layout. */
.scroll-hint-anchor {
  position: sticky;
  bottom: 0;
  height: 0;
  margin-top: -1rem;
  z-index: 2;
}

.scroll-hint {
  position: absolute;
  left: calc(-1 * var(--about-pad-x));
  right: calc(-1 * var(--about-pad-x));
  bottom: calc(-1 * var(--about-pad-y));
  height: 96px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 0.9rem;
  background: linear-gradient(180deg, rgba(19, 25, 38, 0) 0%, rgba(19, 25, 38, 0.95) 70%);
  pointer-events: none;
}

.scroll-hint-btn {
  pointer-events: auto;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 21, 31, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(245, 158, 11, 0.45);
  color: #fbbf24;
  cursor: pointer;
  box-shadow: 0 6px 16px -6px rgba(0, 0, 0, 0.7);
  animation: nudge 1.8s ease-in-out infinite;
}

.scroll-hint-btn:hover {
  background: var(--ice-bg);
  border-color: var(--ice-border);
  color: var(--ice-text);
}

@keyframes nudge {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(4px);
  }
}

.hint-enter-active,
.hint-leave-active {
  transition: opacity 0.25s ease;
}

.hint-enter-from,
.hint-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .problems,
  .features,
  .steps {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Phones: one column, tighter padding and a smaller heading so the title,
   the language switch and the close button share one line. */
@media (max-width: 640px) {
  :global(.modal-overlay .modal.about-modal) {
    --about-pad-y: 1.25rem;
    --about-pad-x: 1.1rem;
  }

  :global(.modal-overlay .about-modal .modal-title) {
    font-size: 1.3rem;
    letter-spacing: 1px;
  }

  section {
    padding: 0.85rem;
  }

  .problems,
  .features,
  .steps {
    grid-template-columns: 1fr;
  }
}
</style>
