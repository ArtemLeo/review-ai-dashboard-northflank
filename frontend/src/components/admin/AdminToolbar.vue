<template>
  <div class="toolbar">
    <div class="toolbar-group">
      <div class="filter-group">
        <label for="filter-status"> Statuses </label>
        <select
          id="filter-status"
          :value="filters.status ?? ''"
          class="filter-select"
          data-filter="status"
          @change="onFilterChange($event)"
        >
          <option value="">All</option>
          <option value="Pending">Pending</option>
          <option value="Processing">Processing</option>
          <option value="Completed">Completed</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="filter-rating"> Ratings </label>
        <select
          id="filter-rating"
          :value="filters.rating ?? ''"
          class="filter-select"
          data-filter="rating"
          @change="onFilterChange($event)"
        >
          <option value="">All</option>
          <option value="1">1 Star</option>
          <option value="2">2 Stars</option>
          <option value="3">3 Stars</option>
          <option value="4">4 Stars</option>
          <option value="5">5 Stars</option>
        </select>
      </div>

      <div class="filter-group">
        <label for="filter-priority"> Priorities </label>
        <select
          id="filter-priority"
          :value="filters.priority ?? ''"
          class="filter-select"
          data-filter="priority"
          @change="onFilterChange($event)"
        >
          <option value="">All</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
        </select>
      </div>
    </div>

    <span class="toolbar-divider" aria-hidden="true"></span>

    <div class="toolbar-group toolbar-actions">
      <div class="action-item">
        <span class="action-label">Statistics</span>
        <button
          aria-label="Show statistics"
          class="tool-btn statistics-btn"
          @click="emit('show-statistics')"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="btn-icon"
            aria-hidden="true"
          >
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </button>
      </div>

      <div class="action-item">
        <span class="action-label">Refresh</span>
        <button aria-label="Refresh the list" class="tool-btn refresh-btn" @click="emit('refresh')">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="btn-icon"
            aria-hidden="true"
          >
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>

      <div class="action-item">
        <span class="action-label">Export CSV</span>
        <button
          aria-label="Export CSV"
          class="tool-btn"
          data-action="export"
          :disabled="exporting"
          @click="emit('export')"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="btn-icon"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>
      </div>
    </div>

    <PaginationBar v-bind="pagination" @go-to-page="emit('go-to-page', $event)" />
  </div>
</template>

<script setup lang="ts">
import PaginationBar from "@/components/admin/PaginationBar.vue";
import type { PaginationState, ReviewFilterField, ReviewQuery } from "@/types";

/** Filters, actions and pagination shown above the review table. */
defineProps<{
  /** Currently selected filters. */
  filters: ReviewQuery;
  /** True while the CSV export is being downloaded. */
  exporting: boolean;
  /** Everything the pagination bar needs to render the current page. */
  pagination: PaginationState;
}>();

const emit = defineEmits<{
  /** Emitted with the changed filter and the raw value of its select. */
  "filter-change": [field: ReviewFilterField, value: string];
  /** Emitted when the statistics button is pressed. */
  "show-statistics": [];
  /** Emitted when the refresh button is pressed. */
  refresh: [];
  /** Emitted when the export button is pressed. */
  export: [];
  /** Emitted with the page picked in the pagination bar. */
  "go-to-page": [page: number];
}>();

/** Reports the value picked in one of the filter selects. */
function onFilterChange(event: Event): void {
  const target = event.target as HTMLSelectElement;
  emit("filter-change", target.dataset.filter as ReviewFilterField, target.value);
}
</script>

<style scoped>
/* The toolbar reads left to right in three groups, like the header:
   the filters that narrow the list, the actions, then the pagination. */
.toolbar {
  padding: 1.25rem 2rem;
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
  flex: 0 0 auto;
  background: linear-gradient(180deg, rgba(27, 34, 48, 0.86) 0%, rgba(19, 25, 36, 0.8) 100%);
  backdrop-filter: blur(14px) saturate(120%);
  -webkit-backdrop-filter: blur(14px) saturate(120%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow:
    0 24px 44px -22px rgba(0, 0, 0, 0.72),
    0 8px 18px -12px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

/* The filters share one recessed niche with their captions above. */
.toolbar-group {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.6rem 0.9rem 0.75rem;
  background: linear-gradient(180deg, rgba(30, 38, 54, 0.85) 0%, rgba(22, 28, 41, 0.85) 100%);
  border-radius: 8px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    inset 0 -1px 0 rgba(0, 0, 0, 0.2),
    inset 0 0 0 1px rgba(255, 255, 255, 0.03);
}

/* Hairline between the filters and the actions, as in the header. */
.toolbar-divider {
  align-self: center;
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.12);
}

/* The actions get the same niche as the filters; each one is a column
   with its caption above a round icon button. */
.toolbar-actions {
  gap: 1.1rem;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

/* The pager sits at the right edge. It is targeted by its own class: when
   it is hidden (one page) the actions group must stay where it is. */
.toolbar > .pagination-panel {
  padding: 0 0.5rem 0.75rem;
  margin-left: auto;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label,
.action-label {
  font-family: "Rajdhani", sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #a0aec0;
  white-space: nowrap;
}

.filter-select {
  height: 38px;
  box-sizing: border-box;
  padding: 0 2rem 0 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  font-size: 0.9rem;
  min-width: 110px;
  background-color: rgba(8, 11, 17, 0.55);
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><path fill="%23a0aec0" d="M6 9L1 4h10z"/></svg>');
  background-repeat: no-repeat;
  background-position: right 0.9rem center;
  color: #f1f5f9;
  box-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.45),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
  font-family: "Inter", sans-serif;
  transition: all 0.2s ease;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}

.filter-select:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
}

/* Round amber icon buttons, as tall as the selects so every control of
   the toolbar shares one bottom line. */
.tool-btn {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  color: #1c1305;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.tool-btn:hover {
  background: linear-gradient(180deg, #fcd34d 0%, #f59e0b 58%, #e08e05 100%);
  transform: translateY(-1px);
  box-shadow:
    0 8px 18px -4px rgba(245, 158, 11, 0.35),
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

.tool-btn:disabled {
  background: rgba(245, 158, 11, 0.45);
  color: rgba(28, 19, 5, 0.7);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-icon {
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.refresh-btn:hover .btn-icon {
  transform: rotate(45deg);
}

/* Narrow screens: the groups stack, the divider is no longer needed. */
@media (max-width: 900px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .toolbar-divider {
    display: none;
  }

  /* A definite width lets the wrapping filter row take the height of the
     one line it uses, instead of leaving an empty band above it. */
  .toolbar > .toolbar-group {
    width: 100%;
  }

  .filter-group {
    flex: 1 1 120px;
  }

  .filter-select {
    width: 100%;
  }

  .toolbar-actions {
    justify-content: space-around;
  }

  .toolbar > .pagination-panel {
    padding: 0;
    margin-left: 0;
  }
}
</style>
