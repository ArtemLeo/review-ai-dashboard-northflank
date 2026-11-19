// @vitest-environment jsdom
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reviewService } from "@/services/reviewService";
import { useReviewsStore } from "@/stores/reviews";
import { makeReview } from "@/test/fixtures";
import { AnalysisStatus, Priority } from "@/types";
import type { AdminReviewDto } from "@/types";

vi.mock("@/services/reviewService", () => ({
  reviewService: {
    getReviews: vi.fn(),
    updateReviewStatus: vi.fn(),
    regenerateDraftResponse: vi.fn(),
    getStatistics: vi.fn(),
    exportReviews: vi.fn(),
  },
}));

describe("reviews store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("loads the first page with the active filters", async () => {
    vi.mocked(reviewService.getReviews).mockResolvedValue({
      items: [makeReview()],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    const store = useReviewsStore();

    await store.applyFilters({ status: AnalysisStatus.Pending });

    expect(store.reviews).toHaveLength(1);
    expect(store.total).toBe(1);
    expect(reviewService.getReviews).toHaveBeenCalledWith(
      expect.objectContaining({ status: AnalysisStatus.Pending, page: 1 })
    );
    expect(store.loading).toBe(false);
  });

  it("drops a slow answer to an older request", async () => {
    let answerOld: (value: Awaited<ReturnType<typeof reviewService.getReviews>>) => void = () => {};
    vi.mocked(reviewService.getReviews)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            answerOld = resolve;
          })
      )
      .mockResolvedValueOnce({
        items: [makeReview({ id: "new" })],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      });
    const store = useReviewsStore();

    const oldRequest = store.applyFilters({ status: AnalysisStatus.Pending });
    await store.applyFilters({ status: AnalysisStatus.Completed });
    answerOld({
      items: [makeReview({ id: "old" })],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    await oldRequest;

    expect(store.reviews.map((r) => r.id)).toEqual(["new"]);
    expect(store.loading).toBe(false);
  });

  it("ignores a page outside the valid range", async () => {
    const store = useReviewsStore();

    await store.loadPage(5);

    expect(reviewService.getReviews).not.toHaveBeenCalled();
  });

  it("keeps the error message and rethrows when loading fails", async () => {
    vi.mocked(reviewService.getReviews).mockRejectedValue(new Error("boom"));
    const store = useReviewsStore();

    await expect(store.loadPage(1)).rejects.toThrow("boom");

    expect(store.error).toBe("Something went wrong. Please try again later");
    expect(store.loading).toBe(false);
  });

  it("replaces the review in place after the draft is regenerated", async () => {
    vi.mocked(reviewService.getReviews).mockResolvedValue({
      items: [makeReview()],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    vi.mocked(reviewService.regenerateDraftResponse).mockResolvedValue(
      makeReview({ ai_draft_response: "A new draft" })
    );
    const store = useReviewsStore();
    await store.applyFilters();

    const pending = store.regenerateDraftResponse("review-1");
    expect(store.regeneratingIds.has("review-1")).toBe(true);
    await pending;

    expect(store.regeneratingIds.size).toBe(0);
    expect(store.reviews[0].ai_draft_response).toBe("A new draft");
  });

  it("clears the regenerating flag when the request fails", async () => {
    vi.mocked(reviewService.regenerateDraftResponse).mockRejectedValue(new Error("boom"));
    const store = useReviewsStore();

    await expect(store.regenerateDraftResponse("review-1")).rejects.toThrow();

    expect(store.regeneratingIds.size).toBe(0);
  });

  it("leaves the list state alone when a single review is updated", async () => {
    vi.mocked(reviewService.updateReviewStatus).mockRejectedValue(new Error("boom"));
    const store = useReviewsStore();

    await expect(store.updateStatus("review-1", AnalysisStatus.Completed)).rejects.toThrow();

    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it("refreshes status-filtered rows and counts when a review leaves the filter", async () => {
    vi.mocked(reviewService.getReviews)
      .mockResolvedValueOnce({
        items: [makeReview()],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      });
    vi.mocked(reviewService.updateReviewStatus).mockResolvedValue(
      makeReview({ analysis_status: AnalysisStatus.Processing })
    );
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending });

    await store.updateStatus("review-1", AnalysisStatus.Processing);

    expect(store.reviews).toEqual([]);
    expect(store.total).toBe(0);
    expect(store.totalPages).toBe(0);
  });

  it("returns to the last valid page when a status change empties the final page", async () => {
    vi.mocked(reviewService.getReviews)
      .mockResolvedValueOnce({
        items: [makeReview()],
        total: 11,
        page: 1,
        page_size: 10,
        total_pages: 2,
      })
      .mockResolvedValueOnce({
        items: [makeReview()],
        total: 11,
        page: 2,
        page_size: 10,
        total_pages: 2,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 10,
        page: 2,
        page_size: 10,
        total_pages: 1,
      })
      .mockResolvedValueOnce({
        items: [makeReview({ id: "remaining" })],
        total: 10,
        page: 1,
        page_size: 10,
        total_pages: 1,
      });
    vi.mocked(reviewService.updateReviewStatus).mockResolvedValue(
      makeReview({ analysis_status: AnalysisStatus.Completed })
    );
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending });
    await store.loadPage(2);

    await store.updateStatus("review-1", AnalysisStatus.Completed);

    expect(store.page).toBe(1);
    expect(store.total).toBe(10);
    expect(store.reviews[0].id).toBe("remaining");
  });

  it("preserves a requested page when a status update finishes before navigation", async () => {
    let finishNavigation: (
      value: Awaited<ReturnType<typeof reviewService.getReviews>>
    ) => void = () => {};
    let finishStatus: (value: AdminReviewDto) => void = () => {};
    vi.mocked(reviewService.getReviews)
      .mockResolvedValueOnce({
        items: [makeReview()],
        total: 20,
        page: 1,
        page_size: 10,
        total_pages: 2,
      })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishNavigation = resolve;
          })
      )
      .mockImplementation(async (query) => ({
        items: [makeReview({ id: "refreshed" })],
        total: 19,
        page: query?.page ?? 1,
        page_size: 10,
        total_pages: 2,
      }));
    vi.mocked(reviewService.updateReviewStatus).mockImplementation(
      () =>
        new Promise((resolve) => {
          finishStatus = resolve;
        })
    );
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending });
    const update = store.updateStatus("review-1", AnalysisStatus.Processing);
    const navigation = store.loadPage(2);

    finishStatus(makeReview({ analysis_status: AnalysisStatus.Processing }));
    await update;
    finishNavigation({
      items: [makeReview({ id: "stale" })],
      total: 20,
      page: 2,
      page_size: 10,
      total_pages: 2,
    });
    await navigation;

    expect(store.page).toBe(2);
    expect(store.reviews[0].id).toBe("refreshed");
    expect(store.total).toBe(19);
  });

  it("does not let a last-page correction overwrite a newer filter selection", async () => {
    let finishCorrection: (
      value: Awaited<ReturnType<typeof reviewService.getReviews>>
    ) => void = () => {};
    const response = {
      items: [makeReview()],
      total: 11,
      page: 1,
      page_size: 10,
      total_pages: 2,
    };
    vi.mocked(reviewService.getReviews)
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce({ ...response, page: 2 })
      .mockResolvedValueOnce({ ...response, items: [], total: 10, page: 2, total_pages: 1 })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishCorrection = resolve;
          })
      )
      .mockResolvedValueOnce({
        ...response,
        items: [makeReview({ id: "completed", analysis_status: AnalysisStatus.Completed })],
        total: 1,
        total_pages: 1,
      });
    vi.mocked(reviewService.updateReviewStatus).mockResolvedValue(
      makeReview({ analysis_status: AnalysisStatus.Processing })
    );
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending });
    await store.loadPage(2);
    const update = store.updateStatus("review-1", AnalysisStatus.Processing);
    // Allow the now-empty page response to start its replacement request.
    await vi.waitFor(() => expect(reviewService.getReviews).toHaveBeenCalledTimes(4));

    await store.applyFilters({ status: AnalysisStatus.Completed });
    finishCorrection({
      ...response,
      items: [makeReview({ id: "old-filter" })],
      total: 10,
      total_pages: 1,
    });
    await update;

    expect(store.page).toBe(1);
    expect(store.total).toBe(1);
    expect(store.reviews[0].id).toBe("completed");
    expect(store.loading).toBe(false);
  });

  it("does not report a saved status as failed when the filtered list refresh fails", async () => {
    vi.mocked(reviewService.getReviews)
      .mockResolvedValueOnce({
        items: [makeReview()],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      })
      .mockRejectedValueOnce(new Error("List unavailable"));
    const updated = makeReview({ analysis_status: AnalysisStatus.Completed });
    vi.mocked(reviewService.updateReviewStatus).mockResolvedValue(updated);
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending });

    await expect(store.updateStatus("review-1", AnalysisStatus.Completed)).resolves.toEqual(
      updated
    );

    expect(store.error).not.toBeNull();
    expect(store.reviews[0].analysis_status).toBe(AnalysisStatus.Completed);
  });

  it("downloads the filtered reviews as a dated CSV file", async () => {
    vi.mocked(reviewService.getReviews).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });
    vi.mocked(reviewService.exportReviews).mockResolvedValue(new Blob(["id\n"]));
    // jsdom has no object URLs, so the test supplies them and puts back
    // whatever was there before.
    const originalUrls = {
      createObjectURL: URL.createObjectURL,
      revokeObjectURL: URL.revokeObjectURL,
    };
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL: vi.fn(() => "blob:csv"), revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const store = useReviewsStore();
    await store.applyFilters({ status: AnalysisStatus.Pending, priority: Priority.High });

    try {
      await store.exportReviews();
    } finally {
      Object.assign(URL, originalUrls);
    }
    // Restoring the spy forgets its calls, so they are read first.
    const clicks = click.mock.calls.length;
    const link = click.mock.contexts[0] as HTMLAnchorElement | undefined;
    click.mockRestore();

    expect(reviewService.exportReviews).toHaveBeenCalledWith({
      status: AnalysisStatus.Pending,
      priority: Priority.High,
    });
    expect(clicks).toBe(1);
    expect(link?.download).toMatch(/^reviews-\d{4}-\d{2}-\d{2}\.csv$/);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:csv");
  });

  it("marks only the review whose draft is being regenerated", async () => {
    let finish: (value: AdminReviewDto) => void = () => {};
    vi.mocked(reviewService.regenerateDraftResponse).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        })
    );
    const store = useReviewsStore();

    const pending = store.regenerateDraftResponse("review-7");
    expect([...store.regeneratingIds]).toEqual(["review-7"]);
    finish(makeReview({ id: "review-7" }));
    await pending;

    expect(store.regeneratingIds.size).toBe(0);
  });

  it("keeps marking the first review while a second draft is regenerated", async () => {
    const finish = new Map<string, (value: AdminReviewDto) => void>();
    vi.mocked(reviewService.regenerateDraftResponse).mockImplementation(
      (id: string) =>
        new Promise((resolve) => {
          finish.set(id, resolve);
        })
    );
    const store = useReviewsStore();

    const first = store.regenerateDraftResponse("review-a");
    const second = store.regenerateDraftResponse("review-b");
    finish.get("review-b")?.(makeReview({ id: "review-b" }));
    await second;

    expect(store.regeneratingIds.has("review-a")).toBe(true);
    finish.get("review-a")?.(makeReview({ id: "review-a" }));
    await first;
    expect(store.regeneratingIds.size).toBe(0);
  });

  it("forgets every loaded review on clear", async () => {
    vi.mocked(reviewService.getReviews).mockResolvedValue({
      items: [makeReview()],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    const store = useReviewsStore();
    await store.applyFilters();

    store.clear();

    expect(store.reviews).toEqual([]);
    expect(store.total).toBe(0);
    expect(store.error).toBeNull();
  });
});
