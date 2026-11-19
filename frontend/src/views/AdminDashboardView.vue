<template>
  <div class="admin-dashboard">
    <AdminHeader
      :is-dark="isDark"
      @toggle-theme="toggleTheme"
      @logout="handleLogout"
      @about="aboutOpen = true"
    />

    <AdminToolbar
      :filters="filters"
      :exporting="exporting"
      :pagination="pagination"
      @filter-change="onFilterChange"
      @show-statistics="showStatistics"
      @refresh="fetchReviews"
      @export="exportReviews"
      @go-to-page="goToPage"
    />

    <div v-if="loading" class="loading" aria-live="polite">
      <div class="spinner" role="status"></div>
      <span>Loading reviews...</span>
    </div>

    <div v-else-if="error" class="error" role="alert">
      {{ error }}
    </div>

    <div v-else-if="reviewsStore.reviews.length === 0" class="empty">No reviews found</div>

    <div v-else class="table-wrap">
      <ReviewTable
        :reviews="reviewsStore.reviews"
        :current-page="currentPage"
        :page-size="reviewsStore.pageSize"
        @select="selectReview"
      />
    </div>

    <ReviewDetailModal
      ref="detailModal"
      :open="selectedReview !== null"
      :review="selectedReview"
      @close="closeModal"
      @update-status="onStatusChange"
      @regenerate-draft="onRegenerateDraft"
    />

    <div v-if="notice" class="notice" role="alert">
      <span>{{ notice }}</span>
      <button class="notice-close" type="button" aria-label="Dismiss" @click="notice = null">
        ×
      </button>
    </div>

    <StatisticsModal
      :open="showStatsModal"
      :statistics="reviewsStore.statistics"
      :loading="statsLoading"
      :error="statsError"
      @close="closeStatsModal"
    />

    <AboutModal :open="aboutOpen" @close="aboutOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  AnalysisStatus,
  type AdminReviewDto,
  type PaginationState,
  type Priority,
  type Rating,
  type ReviewFilterField,
  type ReviewQuery,
} from "@/types";
import { useAuthStore } from "@/stores/auth";
import { useReviewsStore } from "@/stores/reviews";
import AdminHeader from "@/components/admin/AdminHeader.vue";
import AdminToolbar from "@/components/admin/AdminToolbar.vue";
import ReviewDetailModal from "@/components/admin/ReviewDetailModal.vue";
import ReviewTable from "@/components/admin/ReviewTable.vue";
import StatisticsModal from "@/components/admin/StatisticsModal.vue";
import AboutModal from "@/components/AboutModal.vue";
import { extractErrorMessage } from "@/utils/errors";
import { pageRange } from "@/utils/pagination";
import { useTheme } from "@/utils/theme";

const router = useRouter();
const authStore = useAuthStore();
const reviewsStore = useReviewsStore();
const { darkTheme: isDark, toggleTheme } = useTheme();

const filters = ref<ReviewQuery>({
  status: undefined,
  rating: undefined,
  priority: undefined,
  sort_by: "created_at_utc",
  descending: true,
});

/**
 * The list state comes straight from the store, which tracks only the
 * latest page request: two quick filter changes can no longer hide the
 * spinner while the newer request is still running.
 */
const loading = computed(() => reviewsStore.loading);
const error = computed(() => reviewsStore.error);

/** Currently selected review shown in the detail modal. */
const selectedReview = ref<AdminReviewDto | null>(null);

/** The detail modal, which puts its status back after a failed change. */
const detailModal = ref<InstanceType<typeof ReviewDetailModal> | null>(null);

/** Statistics modal state */
const showStatsModal = ref(false);
const aboutOpen = ref(false);
const statsLoading = ref(false);
const statsError = ref<string | null>(null);

/** True while the CSV export is being downloaded. */
const exporting = ref(false);

/** Non-blocking message about a failed action (status change, draft regeneration, export). */
const notice = ref<string | null>(null);

/** How long a notice stays on screen before it hides itself. */
const NOTICE_TIMEOUT_MS = 6000;
let noticeTimer: ReturnType<typeof setTimeout> | null = null;

function showNotice(error: unknown): void {
  notice.value = extractErrorMessage(error);
  if (noticeTimer !== null) clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    notice.value = null;
    noticeTimer = null;
  }, NOTICE_TIMEOUT_MS);
}

/** Pagination — the backend paginates, so the page only holds the current slice. */
const currentPage = computed(() => reviewsStore.page);
const totalPages = computed(() => Math.max(1, reviewsStore.totalPages));

/** Everything the pagination bar needs to render the current page. */
const pagination = computed<PaginationState>(() => {
  const { start, end } = pageRange(currentPage.value, reviewsStore.pageSize, reviewsStore.total);
  return {
    currentPage: currentPage.value,
    totalPages: totalPages.value,
    rangeStart: start,
    rangeEnd: end,
    total: reviewsStore.total,
  };
});

/**
 * Applies the value picked in one of the filter selects.
 *
 * The toolbar reports the raw select value; it is converted to the
 * enum-typed filter here so that the compiler validates the values.
 */
function onFilterChange(field: ReviewFilterField, raw: string): void {
  if (field === "status") {
    filters.value.status = raw ? (raw as AnalysisStatus) : undefined;
  } else if (field === "rating") {
    filters.value.rating = raw ? (Number(raw) as Rating) : undefined;
  } else {
    filters.value.priority = raw ? (raw as Priority) : undefined;
  }

  void fetchReviews();
}

/**
 * Shows a server answer in the dialog only if the dialog still shows the
 * same review: an answer that arrives after the admin closed the dialog, or
 * opened another review, must not bring the old one back.
 */
function showIfStillOpen(updated: AdminReviewDto): void {
  if (selectedReview.value?.id === updated.id) selectedReview.value = updated;
}

async function selectReview(review: AdminReviewDto): Promise<void> {
  selectedReview.value = review;

  // Automatically update status to Processing only if it's Pending
  if (review.analysis_status === AnalysisStatus.Pending) {
    try {
      showIfStillOpen(await reviewsStore.updateStatus(review.id, AnalysisStatus.Processing));
    } catch (err) {
      console.error("Failed to update status to Processing:", err);
    }
  }
}

function closeModal(): void {
  selectedReview.value = null;
}

async function onStatusChange(status: AnalysisStatus): Promise<void> {
  const review = selectedReview.value;
  if (!review) return;

  try {
    showIfStillOpen(await reviewsStore.updateStatus(review.id, status));
  } catch (err) {
    // Revert the select value and tell the admin why it jumped back.
    detailModal.value?.resetStatus();
    showNotice(err);
  }
}

/**
 * Regenerates the AI draft response for the review shown in the modal and
 * refreshes the modal's copy with the new draft.
 */
async function onRegenerateDraft(): Promise<void> {
  const review = selectedReview.value;
  if (!review) return;

  try {
    showIfStillOpen(await reviewsStore.regenerateDraftResponse(review.id));
  } catch (err) {
    showNotice(err);
  }
}

async function goToPage(page: number): Promise<void> {
  if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
    try {
      await reviewsStore.loadPage(page);
    } catch (e: unknown) {
      // The store keeps the message and the error panel shows it.
      console.error("Error loading the page:", e);
    }
  }
}

async function handleLogout(): Promise<void> {
  try {
    await authStore.logout();
  } catch (err) {
    showNotice(err);
    return;
  }
  // The login page takes the dashboard's place in the history, so Back does
  // not lead to a dashboard the user has just left.
  await router.replace({ name: "admin-login" });
}

/** Applies the current filter selection and reloads from the first page. */
async function fetchReviews(): Promise<void> {
  try {
    await reviewsStore.applyFilters(filters.value);
  } catch (e: unknown) {
    // The store keeps the message; the error panel shows it.
    console.error("Error fetching reviews:", e);
  }
}

async function showStatistics(): Promise<void> {
  showStatsModal.value = true;
  statsLoading.value = true;
  statsError.value = null;

  try {
    await reviewsStore.loadStatistics();
  } catch (e: unknown) {
    console.error("Error fetching statistics:", e);
    statsError.value = extractErrorMessage(e);
  } finally {
    statsLoading.value = false;
  }
}

function closeStatsModal(): void {
  showStatsModal.value = false;
}

/**
 * Downloads the currently filtered reviews as a CSV file.
 *
 * A failure is shown as a dismissible notice — the review list stays
 * usable, so there is no reason to interrupt the admin with a modal.
 */
async function exportReviews(): Promise<void> {
  exporting.value = true;
  try {
    await reviewsStore.exportReviews();
  } catch (e: unknown) {
    showNotice(e);
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  void fetchReviews();
});

onUnmounted(() => {
  if (noticeTimer !== null) clearTimeout(noticeTimer);
});
</script>

<style scoped>
/* Calm, low-contrast backdrop: a deep slate gradient with two very
   soft glows. No busy imagery, so the table stays the focus and the
   eyes do not tire over a long working session. */
/* The dashboard is a vertical stack: the header and the toolbar keep their
   natural height, and the table area takes whatever screen space is left. */
.admin-dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #0d111b;
  background-image:
    radial-gradient(1100px 520px at 12% -8%, rgba(56, 189, 248, 0.07), transparent 65%),
    radial-gradient(900px 480px at 100% 0%, rgba(245, 158, 11, 0.05), transparent 60%),
    linear-gradient(180deg, #10151f 0%, #141a27 45%, #0e131d 100%);
  background-attachment: fixed;
  color: #e2e8f0;
  font-family: "Inter", sans-serif;
}

/* The area below the toolbar: it takes the screen height that is left. */
.table-wrap {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
}

/* The list spans the screen width, never the table's own minimum width, so
   on a phone the table scrolls inside its panel instead of the whole page. */
.table-wrap :deep(.reviews-list) {
  flex: 0 0 auto;
  min-width: 0;
}

/* The loading, error and empty states are raised panels too, so the
   dashboard never falls back to bare text on the backdrop. */
.loading,
.error,
.empty {
  margin: 2rem;
  padding: 3.5rem 2rem;
  text-align: center;
  color: #a0aec0;
  font-size: 1.1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  background: linear-gradient(180deg, #1b2231 0%, #131926 100%);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 12px;
  box-shadow:
    0 24px 48px -20px rgba(0, 0, 0, 0.7),
    0 3px 10px -2px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
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

.error {
  color: #fca5a5;
}

/* Floating notice for failed actions; sits above the modals (z-index 1000). */
.notice {
  position: fixed;
  left: 50%;
  bottom: 1.5rem;
  transform: translateX(-50%);
  z-index: 1100;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  max-width: calc(100vw - 2rem);
  padding: 0.75rem 1rem;
  color: #fecaca;
  font-size: 0.95rem;
  background: #2a1517;
  border: 1px solid rgba(248, 113, 113, 0.45);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

.notice-close {
  flex-shrink: 0;
  padding: 0 0.25rem;
  color: inherit;
  font-size: 1.25rem;
  line-height: 1;
  background: none;
  border: none;
  cursor: pointer;
}
</style>
