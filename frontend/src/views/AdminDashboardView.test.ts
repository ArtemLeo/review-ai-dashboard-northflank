// @vitest-environment jsdom
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reviewService } from "@/services/reviewService";
import { useAuthStore } from "@/stores/auth";
import { useReviewsStore } from "@/stores/reviews";
import { apiError, makeReview } from "@/test/fixtures";
import { AnalysisStatus } from "@/types";
import type { AdminReviewDto } from "@/types";
import AdminDashboardView from "@/views/AdminDashboardView.vue";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({ useRouter: () => ({ push, replace }) }));

vi.mock("@/services/reviewService", () => ({
  reviewService: {
    getReviews: vi.fn(),
    updateReviewStatus: vi.fn(),
    regenerateDraftResponse: vi.fn(),
    getStatistics: vi.fn(),
    exportReviews: vi.fn(),
  },
}));

const service = vi.mocked(reviewService);

const processing = makeReview({
  analysis_status: AnalysisStatus.Processing,
  ai_draft_response: "First draft",
});

async function mountDashboard() {
  const wrapper = mount(AdminDashboardView);
  await flushPromises();
  return wrapper;
}

async function openFirstReview(wrapper: Awaited<ReturnType<typeof mountDashboard>>) {
  await wrapper.get("tbody tr").trigger("click");
  await flushPromises();
}

describe("AdminDashboardView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    service.getReviews.mockResolvedValue({
      items: [processing],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
  });

  it("loads the first page and renders a row per review", async () => {
    const wrapper = await mountDashboard();

    expect(service.getReviews).toHaveBeenCalledTimes(1);
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
    expect(wrapper.text()).toContain("Test User");
  });

  it("shows the empty state when nothing matches", async () => {
    service.getReviews.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
    });

    const wrapper = await mountDashboard();

    expect(wrapper.text()).toContain("No reviews found");
  });

  it("regenerates the draft with exactly one request per click", async () => {
    service.regenerateDraftResponse.mockResolvedValue({
      ...processing,
      ai_draft_response: "New draft",
    });
    const wrapper = await mountDashboard();
    await openFirstReview(wrapper);

    await wrapper.get(".regenerate-btn").trigger("click");
    await flushPromises();

    expect(service.regenerateDraftResponse).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("New draft");
    expect(wrapper.find(".notice").exists()).toBe(false);
  });

  it("shows the backend message when the AI provider fails", async () => {
    service.regenerateDraftResponse.mockRejectedValue(
      apiError(502, "The AI provider is unavailable right now. Please try again in a moment")
    );
    const wrapper = await mountDashboard();
    await openFirstReview(wrapper);

    await wrapper.get(".regenerate-btn").trigger("click");
    await flushPromises();

    expect(wrapper.get(".notice").text()).toContain("The AI provider is unavailable");
    expect(wrapper.text()).toContain("First draft");

    await wrapper.get(".notice-close").trigger("click");
    expect(wrapper.find(".notice").exists()).toBe(false);
  });

  it("reports a failed export without hiding the list", async () => {
    service.exportReviews.mockRejectedValue(apiError(500, ""));
    const wrapper = await mountDashboard();

    await wrapper.get('button[data-action="export"]').trigger("click");
    await flushPromises();

    expect(wrapper.get(".notice span").text()).toBe("Server error. Please try again later");
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
  });

  it("moves a pending review to processing when it is opened", async () => {
    const pending = makeReview();
    service.getReviews.mockResolvedValue({
      items: [pending],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    service.updateReviewStatus.mockResolvedValue({
      ...pending,
      analysis_status: AnalysisStatus.Processing,
    });
    const wrapper = await mountDashboard();

    await openFirstReview(wrapper);

    expect(service.updateReviewStatus).toHaveBeenCalledWith("review-1", AnalysisStatus.Processing);
  });

  it("saves a manual status after the automatic Processing update finishes", async () => {
    const pending = makeReview();
    service.getReviews.mockResolvedValue({
      items: [pending],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
    });
    let finishAuto: (value: AdminReviewDto) => void = () => {};
    service.updateReviewStatus
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finishAuto = resolve;
          })
      )
      .mockResolvedValueOnce(makeReview({ analysis_status: AnalysisStatus.Completed }));
    const wrapper = await mountDashboard();
    await wrapper.get("tbody tr").trigger("click");
    await wrapper.get(".modal-status-select").setValue(AnalysisStatus.Completed);

    expect(service.updateReviewStatus).toHaveBeenCalledTimes(1);
    finishAuto(makeReview({ analysis_status: AnalysisStatus.Processing }));
    await flushPromises();

    expect(service.updateReviewStatus.mock.calls.map(([, status]) => status)).toEqual([
      AnalysisStatus.Processing,
      AnalysisStatus.Completed,
    ]);
    expect(useReviewsStore().reviews[0].analysis_status).toBe(AnalysisStatus.Completed);
    expect((wrapper.get(".modal-status-select").element as HTMLSelectElement).value).toBe(
      AnalysisStatus.Completed
    );
    wrapper.unmount();
  });

  it("reports failed logout and leaves the dashboard available for retry", async () => {
    const auth = useAuthStore();
    auth.isAuthenticated = true;
    vi.spyOn(auth, "logout").mockRejectedValue(
      apiError(503, "Sign-in is temporarily unavailable. Please try again in a moment")
    );
    const wrapper = await mountDashboard();

    await wrapper.get(".logout-btn").trigger("click");
    await flushPromises();

    expect(wrapper.get(".notice").text()).toContain("temporarily unavailable");
    expect(push).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
    wrapper.unmount();
  });
});
