<template>
  <div v-if="totalPages > 1" class="pagination-panel">
    <span class="pagination-summary">{{ rangeStart }}–{{ rangeEnd }} of {{ total }}</span>
    <div class="pagination-controls">
      <button
        class="page-btn"
        aria-label="Previous page"
        :disabled="currentPage === 1"
        @click="emit('go-to-page', currentPage - 1)"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <span class="page-indicator" aria-live="polite">
        Page <strong>{{ currentPage }}</strong> / {{ totalPages }}
      </span>
      <button
        class="page-btn"
        aria-label="Next page"
        :disabled="currentPage === totalPages"
        @click="emit('go-to-page', currentPage + 1)"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Compact pager for the admin review list: the shown range, previous and
 * next buttons and a "Page 3 / 11" indicator. It has the same small width
 * on every screen, so it never wraps or widens the toolbar.
 */
defineProps<{
  /** Current page number (1-based). */
  currentPage: number;
  /** Total number of pages available. */
  totalPages: number;
  /** Index of the first review on the current page (1-based). */
  rangeStart: number;
  /** Index of the last review on the current page (1-based). */
  rangeEnd: number;
  /** Total number of reviews matching the current filters. */
  total: number;
}>();

const emit = defineEmits<{
  /** Emitted with the page to navigate to. */
  "go-to-page": [page: number];
}>();
</script>

<style scoped>
.pagination-panel {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-height: 48px;
}

.pagination-summary {
  color: #a0aec0;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  white-space: nowrap;
}

/* The arrows and the indicator share one recessed track, like the theme
   switch in the header. */
.pagination-controls {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: rgba(8, 11, 17, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.45);
}

.page-btn {
  width: 34px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #fbbf24;
  cursor: pointer;
  transition: all 0.15s ease;
}

.page-btn:hover:not(:disabled) {
  background: var(--ice-bg);
  color: var(--ice-text);
}

.page-btn:disabled {
  color: #475569;
  cursor: not-allowed;
}

.page-indicator {
  padding: 0 0.6rem;
  color: #94a3b8;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  white-space: nowrap;
}

/* Rajdhani's space is narrow, so the number gets a little air of its own. */
.page-indicator strong {
  margin-left: 0.3em;
  color: #f8fafc;
}

/* Stacked toolbar on narrow screens: the range left, the pager right. */
@media (max-width: 900px) {
  .pagination-panel {
    justify-content: space-between;
  }
}
</style>
