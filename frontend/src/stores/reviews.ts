import { defineStore } from "pinia";
import { ref } from "vue";
import { reviewService } from "@/services/reviewService";
import { extractErrorMessage } from "@/utils/errors";
import type { AdminReviewDto, AnalysisStatus, ReviewQuery, ReviewStatistics } from "@/types";

/** Empty statistics used before the first successful fetch. */
function emptyStatistics(): ReviewStatistics {
  return {
    rating_1: 0,
    rating_2: 0,
    rating_3: 0,
    rating_4: 0,
    rating_5: 0,
    total: 0,
    avg_rating: 0,
  };
}

/**
 * Pinia store backing the admin review dashboard.
 *
 * Holds the currently loaded page of reviews, the active filters and the
 * statistics reported by the server.  All pagination is server-side.
 */
export const useReviewsStore = defineStore("reviews", () => {
  /** Reviews belonging to the currently loaded page. */
  const reviews = ref<AdminReviewDto[]>([]);
  /** True while a page of the review list is loading. */
  const loading = ref(false);
  /**
   * Ids of the reviews whose AI draft is being regenerated.  A set, not one
   * id: the admin may start a second review's draft before the first one is
   * back, and the first must still show its progress, not a fresh button.
   */
  const regeneratingIds = ref(new Set<string>());
  /** Human-readable error message from the last failed page load, or null. */
  const error = ref<string | null>(null);
  /** Total number of reviews matching the current filters (across all pages). */
  const total = ref(0);
  /** Current page number as reported by the server (1-based). */
  const page = ref(1);
  /** Number of items requested per page. */
  const pageSize = ref(10);
  /** Total number of pages available for the current filters. */
  const totalPages = ref(0);
  /** Ratings distribution reported by the server. */
  const statistics = ref<ReviewStatistics>(emptyStatistics());

  /** Keeps track of the currently active filter set used for every request. */
  const activeQuery = ref<ReviewQuery>({});

  /** Number of the latest page request; older answers are dropped. */
  let latestRequest = 0;
  /** Latest navigation target, including a page whose response is still pending. */
  let requestedPage = 1;
  /** Changes on sign-out so queued mutations cannot reach a later session. */
  let sessionVersion = 0;
  /** Serializes status writes for each review in the operator's chosen order. */
  const statusUpdates = new Map<string, Promise<AdminReviewDto>>();

  /**
   * Reloads a single page of reviews using the active filters.
   * Page targets outside the valid range are ignored.  When filters change
   * quickly, only the answer to the latest request is shown — a slower
   * answer to an older request never overwrites a newer page.
   */
  async function loadPage(targetPage: number): Promise<void> {
    if (targetPage < 1 || targetPage > Math.max(totalPages.value, 1)) {
      return;
    }
    const requestId = ++latestRequest;
    requestedPage = targetPage;
    loading.value = true;
    error.value = null;
    try {
      const response = await reviewService.getReviews({
        ...activeQuery.value,
        page: targetPage,
        page_size: pageSize.value,
      });
      if (requestId !== latestRequest) return;
      const lastPage = Math.max(response.total_pages, 1);
      if (response.page > lastPage) {
        // Correct only the latest response, so an older refresh cannot
        // redirect a newer navigation or filter selection to another page.
        totalPages.value = response.total_pages;
        await loadPage(lastPage);
        return;
      }
      reviews.value = response.items;
      total.value = response.total;
      page.value = response.page;
      pageSize.value = response.page_size;
      totalPages.value = response.total_pages;
    } catch (e: unknown) {
      if (requestId !== latestRequest) return;
      error.value = extractErrorMessage(e);
      throw e;
    } finally {
      if (requestId === latestRequest) loading.value = false;
    }
  }

  /** Applies a new filter set and jumps back to the first page. */
  async function applyFilters(query: ReviewQuery = {}): Promise<void> {
    activeQuery.value = { ...query };
    await loadPage(1);
  }

  /**
   * Updates a review's status in order and refreshes the active status filter.
   */
  async function updateStatus(id: string, status: AnalysisStatus): Promise<AdminReviewDto> {
    const previous = statusUpdates.get(id);
    const requestSession = sessionVersion;
    const pending = (async (): Promise<AdminReviewDto> => {
      // Opening Pending starts a Processing update. A manual selection made
      // before it finishes must reach the server after that automatic write.
      if (previous) await previous.catch(() => undefined);
      if (requestSession !== sessionVersion) {
        throw new Error("The session changed. Please sign in again");
      }
      const updated = await reviewService.updateReviewStatus(id, status);
      if (requestSession !== sessionVersion) return updated;
      const index = reviews.value.findIndex((review) => review.id === id);
      if (index !== -1) reviews.value[index] = updated;

      if (
        activeQuery.value.status &&
        (index === -1 || activeQuery.value.status !== updated.analysis_status)
      ) {
        try {
          await loadPage(requestedPage);
        } catch {
          // The status was saved; a failed list refresh has its own error.
        }
      }
      return updated;
    })();
    statusUpdates.set(id, pending);
    try {
      return await pending;
    } finally {
      if (statusUpdates.get(id) === pending) statusUpdates.delete(id);
    }
  }

  /**
   * Regenerates the AI draft response for a review and refreshes it in place.
   *
   * The operator can keep clicking until they are happy with the generated
   * reply — every call produces a fresh draft for the same review text.
   */
  async function regenerateDraftResponse(id: string): Promise<AdminReviewDto> {
    regeneratingIds.value.add(id);
    try {
      const updated = await reviewService.regenerateDraftResponse(id);
      const index = reviews.value.findIndex((review) => review.id === id);
      if (index !== -1) {
        reviews.value[index] = updated;
      }
      return updated;
    } finally {
      regeneratingIds.value.delete(id);
    }
  }

  /** Loads the ratings distribution for the whole dataset. */
  async function loadStatistics(): Promise<ReviewStatistics> {
    const data = await reviewService.getStatistics();
    statistics.value = data;
    return data;
  }

  /**
   * Downloads the reviews matching the active filters as a CSV file.
   *
   * The file is saved through a temporary object URL, which is revoked
   * right after the click so the browser does not leak the blob.
   */
  async function exportReviews(): Promise<void> {
    const blob = await reviewService.exportReviews(activeQuery.value);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `reviews-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Forgets every loaded review, e.g. on sign-out, so the next session in
   * the same tab never flashes the previous one's data.
   */
  function clear(): void {
    latestRequest += 1;
    sessionVersion += 1;
    statusUpdates.clear();
    requestedPage = 1;
    reviews.value = [];
    total.value = 0;
    page.value = 1;
    totalPages.value = 0;
    statistics.value = emptyStatistics();
    activeQuery.value = {};
    loading.value = false;
    error.value = null;
    regeneratingIds.value.clear();
  }

  return {
    reviews,
    loading,
    error,
    total,
    page,
    pageSize,
    totalPages,
    statistics,
    regeneratingIds,
    loadPage,
    applyFilters,
    updateStatus,
    regenerateDraftResponse,
    loadStatistics,
    exportReviews,
    clear,
  };
});
