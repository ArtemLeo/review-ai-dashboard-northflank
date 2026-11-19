<template>
  <div class="reviews-list">
    <div class="table-wrap">
      <table class="reviews-table">
        <colgroup>
          <col class="col-w-num" />
          <col class="col-w-date" />
          <col class="col-w-author" />
          <col class="col-w-email" />
          <col class="col-w-text" />
          <col class="col-w-priority" />
          <col class="col-w-rating" />
          <col class="col-w-draft" />
          <col class="col-w-badge" />
        </colgroup>
        <thead>
          <tr>
            <th class="col-num">#</th>
            <th>Created Date</th>
            <th>User Name</th>
            <th>User Email</th>
            <th>User Review</th>
            <th>Priority</th>
            <th>Rating</th>
            <th>AI Response</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(review, index) in reviews"
            :key="review.id"
            class="review-row clickable-row"
            tabindex="0"
            :aria-label="`Open the review of ${review.author_name}`"
            @click="emit('select', review)"
            @keydown.enter.prevent="emit('select', review)"
            @keydown.space.prevent="emit('select', review)"
          >
            <td class="num">{{ (currentPage - 1) * pageSize + index + 1 }}</td>
            <td class="date">{{ formatShortDate(review.created_at_utc) }}</td>
            <td class="author">{{ review.author_name }}</td>
            <td class="email">{{ review.email }}</td>
            <td class="text" :lang="review.language_code ?? undefined">
              <span class="language-flag">{{ getLanguageFlag(review.language_code) }}</span>
              {{ review.text }}
            </td>
            <td>
              <span
                v-if="review.priority"
                :class="['badge', 'priority', review.priority.toLowerCase()]"
              >
                {{ review.priority }}
              </span>
              <span v-else class="no-data">-</span>
            </td>
            <td>
              <span
                v-if="review.rating"
                class="star-rating"
                role="img"
                :aria-label="`${review.rating} of 5 stars`"
                >{{ renderStars(review.rating) }}</span
              >
              <span v-else class="no-data">-</span>
            </td>
            <td class="draft-response">
              <span v-if="review.ai_draft_response" class="draft-content">
                {{ review.ai_draft_response }}
              </span>
              <span v-else class="no-data">-</span>
            </td>
            <td>
              <span :class="['badge', 'status', review.analysis_status.toLowerCase()]">
                {{ review.analysis_status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AdminReviewDto } from "@/types";
import { getLanguageFlag } from "@/utils/languageUtils";
import { formatShortDate, renderStars } from "@/utils/format";

/** Read-only table of the reviews on the current page. */
defineProps<{
  /** Reviews rendered in the table. */
  reviews: AdminReviewDto[];
  /** Current page number (1-based). */
  currentPage: number;
  /** Number of reviews per page. */
  pageSize: number;
}>();

const emit = defineEmits<{
  /** Emitted with the review whose row was clicked. */
  select: [review: AdminReviewDto];
}>();
</script>

<style scoped>
.reviews-list {
  padding: 2rem;
}

@media (max-width: 640px) {
  .reviews-list {
    padding: 1rem;
  }
}

/* Rounded panel that clips the table's corners — border-collapse: collapse
   ignores border-radius on the table itself, so the radius lives here.
   It is also the horizontal scroller on narrow screens. */
.table-wrap {
  border-radius: 12px;
  overflow-x: auto;
  overflow-y: hidden;
  border: 1px solid rgba(255, 255, 255, 0.09);
  box-shadow:
    0 30px 60px -18px rgba(0, 0, 0, 0.66),
    0 16px 32px -14px rgba(0, 0, 0, 0.5),
    0 3px 8px -2px rgba(0, 0, 0, 0.4);
}

.reviews-table {
  width: 100%;
  /* Below this width the columns would become unreadable, so the table
     keeps its size and the wrapper scrolls horizontally instead. */
  min-width: 900px;
  border-collapse: collapse;
  table-layout: fixed;
  background: #161d2b;
}

/* Column widths via colgroup, in proportion to the content */
.col-w-num {
  width: 72px;
}
.col-w-date {
  width: 11%;
}
.col-w-author {
  width: 13%;
}
.col-w-email {
  width: 13%;
}
.col-w-priority {
  width: 8.5%;
} /* Priority: wide enough for the "MEDIUM" badge on a 1280px screen */
.col-w-rating {
  width: 10.5%;
} /* Rating: all five stars, never cut to an ellipsis, from 1280px up */
.col-w-badge {
  width: 10%;
} /* Status: wide enough for the "PROCESSING" badge */
.col-w-text {
  width: 18%;
} /* Review Text */
.col-w-draft {
  width: 19%;
} /* AI Draft Response */

.reviews-table thead {
  background: linear-gradient(180deg, #1c2434 0%, #121826 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.reviews-table th {
  padding: 1.1rem 0.75rem;
  text-align: center;
  font-family: "Rajdhani", sans-serif;
  font-weight: 700;
  color: #a0aec0;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reviews-table tbody tr {
  transition: background 0.15s ease;
}

/* Very subtle zebra striping — alternate row tint to fight row-flattening.
   The opacity is intentionally low so it provides visual separation without being distracting. */
.reviews-table tbody tr:nth-child(even) {
  background: rgba(250, 250, 251, 0.02);
}

.reviews-table tbody tr:hover {
  background: rgba(245, 158, 11, 0.05) !important;
}

/* Thin grid lines between the body cells — the header stays clean. */
.reviews-table tbody td {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.reviews-table tbody td:last-child {
  border-right: none;
}

.reviews-table tbody tr:last-child td {
  border-bottom: none;
}

.reviews-table td {
  padding: 0.95rem 0.75rem;
  vertical-align: middle;
  text-align: center;
  color: #cbd5e1;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reviews-table td.text,
.reviews-table td.draft-response {
  text-align: left;
}

.reviews-table .author {
  font-weight: 600;
  color: #ffffff;
}

.reviews-table .email {
  color: #94a3b8;
}

.reviews-table .date {
  color: #94a3b8;
  font-size: 0.82rem;
  white-space: nowrap;
}

.reviews-table .text {
  color: #cbd5e1;
}

/* Apple's emoji font has the flags built in; elsewhere, Windows above all,
   the system font shows two letters instead, so Noto Color Emoji steps in. */
.language-flag {
  margin-right: 0.5rem;
  font-size: 1rem;
  font-family: "Apple Color Emoji", "Noto Color Emoji", sans-serif;
}

/* The table's stars are a touch more compact than the dialog's, so the
   five of them fit their column on a laptop screen. */
.reviews-table .star-rating {
  font-size: 0.95rem;
  letter-spacing: 1px;
}

.reviews-table .draft-response {
  color: #6ee7b7;
}

.draft-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.reviews-table .no-data {
  color: #475569;
}

/* Row number column */
.reviews-table .col-num {
  text-align: center;
  color: #4a5568;
}

.reviews-table .num {
  text-align: center;
  color: #94a3b8;
  font-size: 0.8rem;
  font-family: "Rajdhani", sans-serif;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

/* Clickable row; keyboard users reach it with Tab and open it with Enter. */
.clickable-row {
  cursor: pointer;
}

.clickable-row:focus-visible {
  outline: 2px solid rgba(245, 158, 11, 0.7);
  outline-offset: -2px;
}

/* Hover hint, centred over the row after a short reading delay. */
.review-row {
  position: relative;
}

.review-row::after {
  content: "Click to view full details";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #1c2434;
  color: #fbbf24;
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.4px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  z-index: 20;
  border: 1px solid rgba(245, 158, 11, 0.25);
  box-shadow:
    0 2px 8px -2px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: opacity 0.2s ease;
  transition-delay: 1000ms;
}

.review-row:hover::after {
  opacity: 1;
}

html[data-theme="light"] .review-row::after {
  background: #eef1f5;
  color: #b45309;
  border: 1px solid rgba(15, 23, 42, 0.2);
  box-shadow:
    0 2px 8px -2px rgba(15, 23, 42, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

/* Light theme: a soft cool grey instead of pure white, so the table does
   not glare next to the dark header and toolbar. */
html[data-theme="light"] .table-wrap {
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow:
    0 30px 60px -18px rgba(15, 23, 42, 0.08),
    0 16px 32px -14px rgba(15, 23, 42, 0.08),
    0 3px 8px -2px rgba(15, 23, 42, 0.04);
}

html[data-theme="light"] .reviews-table {
  background: #e4e8ee;
}

/* Light theme: darker header captions and badge text, so every label keeps
   a readable contrast on the grey surface. */
html[data-theme="light"] .reviews-table th {
  color: #475569;
}

html[data-theme="light"] .reviews-table .priority.low,
html[data-theme="light"] .reviews-table .status.pending {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
  border-color: rgba(59, 130, 246, 0.4);
}

html[data-theme="light"] .reviews-table .priority.medium {
  background: rgba(245, 158, 11, 0.16);
  color: #92400e;
  border-color: rgba(217, 119, 6, 0.45);
}

html[data-theme="light"] .reviews-table .priority.high {
  background: rgba(239, 68, 68, 0.14);
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.4);
}

html[data-theme="light"] .reviews-table .status.processing {
  background: rgba(251, 146, 60, 0.16);
  color: #9a3412;
  border-color: rgba(234, 88, 12, 0.4);
}

html[data-theme="light"] .reviews-table .status.completed {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
  border-color: rgba(16, 185, 129, 0.45);
}

html[data-theme="light"] .reviews-table thead {
  background: linear-gradient(180deg, #d9dfe7 0%, #d0d7e0 100%);
  border-bottom: 1px solid rgba(15, 23, 42, 0.1);
}

html[data-theme="light"] .reviews-table tbody td {
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

html[data-theme="light"] .reviews-table td {
  color: #334155;
}

/* The bright amber of the dark theme is too faint on the light rows. */
html[data-theme="light"] .reviews-table .star-rating {
  color: #b45309;
}

html[data-theme="light"] .reviews-table .author {
  color: #0f172a;
}

html[data-theme="light"] .reviews-table .email {
  color: #475569;
}

html[data-theme="light"] .reviews-table .num {
  color: #64748b;
}

html[data-theme="light"] .reviews-table .no-data {
  color: #94a3b8;
}

/* Light theme: subtle zebra striping on the grey surface. */
html[data-theme="light"] .reviews-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.025);
}
</style>
