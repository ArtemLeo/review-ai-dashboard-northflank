<template>
  <BaseModal
    :open="open"
    title="Review Statistics"
    modal-class="statistics-modal"
    @close="emit('close')"
  >
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <span>Loading statistics...</span>
    </div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else class="statistics-content">
      <div class="stats-summary">
        <div v-for="card in statCards" :key="card.rating" class="stat-card" :class="card.className">
          <div class="stat-label" role="img" :aria-label="starsLabel(card.rating)">
            {{ card.label }}
          </div>
          <div class="stat-value">{{ animatedCounts[card.rating] }}</div>
        </div>
      </div>

      <div class="progress-bars">
        <div v-for="bar in progressBars" :key="bar.rating" class="progress-item">
          <div class="progress-label" role="img" :aria-label="starsLabel(bar.rating)">
            {{ bar.label }}
          </div>
          <div class="progress-bar-container">
            <div
              class="progress-bar"
              :class="bar.className"
              :style="{ width: animatedPercents[bar.rating] + '%' }"
            ></div>
          </div>
          <div class="progress-value">{{ animatedPercents[bar.rating].toFixed(1) }}%</div>
        </div>
      </div>

      <div class="stats-total">
        <span class="stats-total-item">
          Total Reviews: <strong>{{ statistics.total }}</strong>
        </span>
        <span class="stats-total-separator">·</span>
        <span class="stats-total-item">
          Average Rating:
          <strong class="stats-avg-rating">
            <span class="star-icon" aria-hidden="true">★</span>
            <span class="rating-number">{{ averageRating }}</span>
            <span class="rating-max">/ 5.0</span>
          </strong>
        </span>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import BaseModal from "@/components/admin/BaseModal.vue";
import type { ReviewStatistics } from "@/types";

/** Ratings the dashboard reports on, ordered from the best to the worst. */
const RATINGS = [5, 4, 3, 2, 1] as const;

/** Duration of the count-up animation, in milliseconds. */
const ANIMATION_DURATION_MS = 2400;

/** Spoken name of a row of stars: "1 star", "2 stars", ... */
function starsLabel(rating: number): string {
  return rating === 1 ? "1 star" : `${rating} stars`;
}

type RatingKey = 1 | 2 | 3 | 4 | 5;

/** Animated counters, keyed by rating. */
type RatingMap = Record<RatingKey, number>;

const props = defineProps<{
  /** Whether the dialog is visible. */
  open: boolean;
  /** Statistics to display. */
  statistics: ReviewStatistics;
  /** True while the statistics are being fetched. */
  loading: boolean;
  /** Error message to display instead of the statistics. */
  error: string | null;
}>();

const emit = defineEmits<{
  /** Emitted when the dialog should be dismissed. */
  close: [];
}>();

const animatedCounts = ref<RatingMap>({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 });
const animatedPercents = ref<RatingMap>({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 });

/** Summary cards, ordered from 5 stars down to 1 star. */
const statCards = computed(() =>
  RATINGS.map((rating) => ({
    rating: rating as RatingKey,
    label: "★".repeat(rating),
    className: `rating-${rating}`,
  }))
);

/** Progress bars, ordered from 5 stars down to 1 star. */
const progressBars = computed(() =>
  RATINGS.map((rating) => ({
    rating: rating as RatingKey,
    label: "★".repeat(rating),
    className: `progress-${rating}`,
  }))
);

/**
 * Weighted average rating across the analysed reviews.
 *
 * The backend already computes the average over the reviews that carry a
 * rating, so the value is taken from there.  Dividing the sum of the
 * ratings by the number of *all* reviews would lower the result every
 * time a review is still waiting for its analysis.
 */
const averageRating = computed(() => (props.statistics.avg_rating || 0).toFixed(1));

let animationFrameId: number | null = null;

function stopAnimation(): void {
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
}

/** Animates the counters and percentages towards the reported statistics. */
function animateStatisticsValues(target: ReviewStatistics): void {
  stopAnimation();

  const startTime = performance.now();
  // The percentages describe the share of the *rated* reviews, so the
  // reviews that are still waiting for their analysis do not count.
  const rated =
    target.rating_1 + target.rating_2 + target.rating_3 + target.rating_4 + target.rating_5;

  const targetPercents: RatingMap = {
    1: rated > 0 ? (target.rating_1 / rated) * 100 : 0,
    2: rated > 0 ? (target.rating_2 / rated) * 100 : 0,
    3: rated > 0 ? (target.rating_3 / rated) * 100 : 0,
    4: rated > 0 ? (target.rating_4 / rated) * 100 : 0,
    5: rated > 0 ? (target.rating_5 / rated) * 100 : 0,
  };

  // Visitors who asked the system for less motion see the final values
  // right away instead of the count-up.
  const reduceMotion =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const step = (currentTime: number): void => {
    const progress = reduceMotion
      ? 1
      : Math.min((currentTime - startTime) / ANIMATION_DURATION_MS, 1);
    // Ease-out cubic
    const ease = 1 - Math.pow(1 - progress, 3);

    animatedCounts.value = {
      1: Math.round(target.rating_1 * ease),
      2: Math.round(target.rating_2 * ease),
      3: Math.round(target.rating_3 * ease),
      4: Math.round(target.rating_4 * ease),
      5: Math.round(target.rating_5 * ease),
    };

    animatedPercents.value = {
      1: targetPercents[1] * ease,
      2: targetPercents[2] * ease,
      3: targetPercents[3] * ease,
      4: targetPercents[4] * ease,
      5: targetPercents[5] * ease,
    };

    if (progress < 1) {
      animationFrameId = requestAnimationFrame(step);
    } else {
      animatedCounts.value = {
        1: target.rating_1,
        2: target.rating_2,
        3: target.rating_3,
        4: target.rating_4,
        5: target.rating_5,
      };
      animatedPercents.value = targetPercents;
      animationFrameId = null;
    }
  };

  animationFrameId = requestAnimationFrame(step);
}

// Restart the animation every time the dialog opens or fresh statistics arrive.
watch(
  () => (props.open ? props.statistics : null),
  (value) => {
    if (!value) {
      stopAnimation();
      return;
    }
    animatedCounts.value = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    animatedPercents.value = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    animateStatisticsValues(value);
  },
  { deep: true }
);

onUnmounted(stopAnimation);
</script>

<style scoped>
/* The `statistics-modal` panel rules live in BaseModal, which owns that node. */

.loading,
.error {
  padding: 4rem;
  text-align: center;
  color: #a0aec0;
  font-size: 1.1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.error {
  color: #fca5a5;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(245, 158, 11, 0.2);
  border-top-color: #f59e0b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.statistics-content {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  width: 100%;
}

/* The five summary cards are raised panels in the same dark family as the
   dashboard table; the rating colour only tints the surface. */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  max-width: 650px;
  margin: 0 auto;
  width: 100%;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-card {
  background: linear-gradient(180deg, rgba(28, 35, 50, 0.9), rgba(18, 24, 35, 0.9));
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 10px;
  padding: 0.85rem 0.5rem;
  text-align: center;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
  box-shadow:
    0 8px 18px -8px rgba(0, 0, 0, 0.55),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 14px 26px -10px rgba(0, 0, 0, 0.6),
    0 3px 8px -3px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.stat-card.rating-5 {
  border-color: rgba(16, 185, 129, 0.35);
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.14), rgba(16, 185, 129, 0.03));
  box-shadow:
    0 8px 18px -8px rgba(16, 185, 129, 0.16),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.stat-card.rating-4 {
  border-color: rgba(132, 204, 22, 0.35);
  background: linear-gradient(180deg, rgba(132, 204, 22, 0.14), rgba(132, 204, 22, 0.03));
  box-shadow:
    0 8px 18px -8px rgba(132, 204, 22, 0.16),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.stat-card.rating-3 {
  border-color: rgba(245, 158, 11, 0.38);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.14), rgba(245, 158, 11, 0.03));
  box-shadow:
    0 8px 18px -8px rgba(245, 158, 11, 0.18),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.stat-card.rating-2 {
  border-color: rgba(251, 146, 60, 0.35);
  background: linear-gradient(180deg, rgba(251, 146, 60, 0.14), rgba(251, 146, 60, 0.03));
  box-shadow:
    0 8px 18px -8px rgba(251, 146, 60, 0.16),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.stat-card.rating-1 {
  border-color: rgba(239, 68, 68, 0.35);
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.14), rgba(239, 68, 68, 0.03));
  box-shadow:
    0 8px 18px -8px rgba(239, 68, 68, 0.16),
    0 2px 5px -2px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.stat-label {
  font-size: 1.15rem;
  color: #fbbf24;
  margin-bottom: 0.4rem;
  letter-spacing: 2px;
  text-shadow: 0 2px 10px rgba(245, 158, 11, 0.25);
}

.stat-value {
  font-family: "Rajdhani", sans-serif;
  font-size: 1.7rem;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.1;
  margin-bottom: 0.35rem;
}

.progress-bars {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  max-width: 650px;
  margin: 0 auto;
  width: 100%;
  transform: translateX(12px);
}

.progress-item {
  display: grid;
  grid-template-columns: 85px 1fr 65px;
  align-items: center;
  gap: 1.1rem;
}

.progress-label {
  font-size: 1.05rem;
  color: #fbbf24;
  letter-spacing: 2px;
  justify-self: end;
  white-space: nowrap;
}

/* The track is recessed into the panel, the fill sits on top of it. */
.progress-bar-container {
  height: 22px;
  background: rgba(8, 11, 17, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  overflow: hidden;
  box-shadow:
    inset 0 2px 5px rgba(0, 0, 0, 0.65),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
  position: relative;
}

.progress-bar {
  height: 100%;
  border-radius: 4px;
  width: 0%;
  position: relative;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

/* 5 Stars — Emerald / Mint green gradient */
.progress-5 {
  background: linear-gradient(90deg, #059669 0%, #10b981 100%);
  box-shadow: 0 0 14px rgba(16, 185, 129, 0.5);
}

/* 4 Stars — Lime / Olive green gradient */
.progress-4 {
  background: linear-gradient(90deg, #65a30d 0%, #84cc16 100%);
  box-shadow: 0 0 14px rgba(132, 204, 22, 0.5);
}

/* 3 Stars — Amber / Gold gradient */
.progress-3 {
  background: linear-gradient(90deg, #d97706 0%, #f59e0b 100%);
  box-shadow: 0 0 14px rgba(245, 158, 11, 0.5);
}

/* 2 Stars — Warm Orange gradient */
.progress-2 {
  background: linear-gradient(90deg, #ea580c 0%, #fb923c 100%);
  box-shadow: 0 0 14px rgba(251, 146, 60, 0.5);
}

/* 1 Star — Ruby Red gradient */
.progress-1 {
  background: linear-gradient(90deg, #dc2626 0%, #ef4444 100%);
  box-shadow: 0 0 14px rgba(239, 68, 68, 0.5);
}

.progress-value {
  font-family: "Rajdhani", sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #ffffff;
  justify-self: start;
  letter-spacing: 0.5px;
}

.stats-total {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  font-family: "Rajdhani", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #cbd5e1;
  padding: 0.9rem 1.25rem;
  background: rgba(8, 11, 17, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.45);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.stats-total-item {
  display: inline-flex;
  align-items: baseline;
  gap: 0.25rem;
}

.stats-total strong {
  color: #ffffff;
  font-size: 1.1rem;
  font-weight: 700;
  margin-left: 0.5rem;
}

.star-icon {
  vertical-align: middle;
  font-size: 1.25rem;
  line-height: 1;
  margin-right: 0.4rem;
}

.rating-number,
/* Vue drops the line break between the spans, so the gap is explicit:
   "4.3 / 5.0", not "4.3/ 5.0". */
.rating-max {
  vertical-align: baseline;
  margin-left: 0.25em;
}

.stats-total-separator {
  color: rgba(255, 255, 255, 0.25);
  font-size: 1.2rem;
}

.stats-avg-rating {
  color: #f59e0b !important;
  font-size: 1.1rem;
}

/* Phones: the cards wrap instead of overflowing the dialog, the bars share
   one grid so they stay aligned, and the totals wrap onto two lines. */
@media (max-width: 640px) {
  .stats-summary {
    grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  }

  .stat-label {
    font-size: 0.85rem;
    letter-spacing: 1px;
  }

  .progress-bars {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr) max-content;
    align-items: center;
    gap: 0.9rem 0.6rem;
    transform: none;
  }

  .progress-item {
    display: contents;
  }

  .progress-label {
    font-size: 0.9rem;
    letter-spacing: 1px;
  }

  .progress-value {
    font-size: 1rem;
  }

  .stats-total {
    flex-wrap: wrap;
    gap: 0.4rem 1rem;
    padding: 0.75rem 1rem;
    font-size: 0.95rem;
    letter-spacing: 0.5px;
  }

  .stats-total-item {
    flex-wrap: wrap;
    justify-content: center;
  }

  .stats-total-separator {
    display: none;
  }
}
</style>
