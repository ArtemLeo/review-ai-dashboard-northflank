// @vitest-environment jsdom
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReviewDetailModal from "@/components/admin/ReviewDetailModal.vue";
import { useReviewsStore } from "@/stores/reviews";
import { makeReview } from "@/test/fixtures";
import { AnalysisStatus, Priority } from "@/types";

const draftReview = makeReview({
  analysis_status: AnalysisStatus.Processing,
  priority: Priority.High,
  rating: 2,
  ai_draft_response: "Sorry for the trouble, we are on it.",
});

describe("ReviewDetailModal", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders nothing while closed", () => {
    const wrapper = mount(ReviewDetailModal, { props: { open: false, review: null } });

    expect(wrapper.find("[role='dialog']").exists()).toBe(false);
  });

  it("shows the review, its status and the AI draft", () => {
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    expect(wrapper.get(".modal-title").text()).toBe("Test User");
    expect(wrapper.text()).toContain("test@example.com");
    expect(wrapper.text()).toContain("The app crashes on start.");
    expect(wrapper.text()).toContain("Sorry for the trouble, we are on it.");
    expect((wrapper.get(".modal-status-select").element as HTMLSelectElement).value).toBe(
      "Processing"
    );
  });

  it("confirms a copy with a check mark that fades back", async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    const button = wrapper.get(".modal-text .modal-field-copy-btn");
    await button.trigger("click");
    await flushPromises();

    expect(writeText).toHaveBeenCalledWith("The app crashes on start.");
    expect(button.classes()).toContain("copied");
    expect(button.text()).toContain("Copied!");

    vi.advanceTimersByTime(2000);
    await flushPromises();
    expect(button.classes()).not.toContain("copied");
    vi.useRealTimers();
  });

  it("emits the picked status", async () => {
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    await wrapper.get(".modal-status-select").setValue("Completed");

    expect(wrapper.emitted("update-status")).toEqual([["Completed"]]);
  });

  it("only asks the parent to regenerate, so one click is one AI call", async () => {
    const store = useReviewsStore();
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    await wrapper.get(".regenerate-btn").trigger("click");

    expect(wrapper.emitted("regenerate-draft")).toHaveLength(1);
    expect(store.regeneratingIds.size).toBe(0);
  });

  it("replaces the button with a progress indicator while regenerating", async () => {
    const store = useReviewsStore();
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    store.regeneratingIds.add(draftReview.id);
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".regenerate-btn").exists()).toBe(false);
    expect(wrapper.find(".regenerate-status").exists()).toBe(true);
  });

  it("keeps the button on a review whose draft is not being regenerated", async () => {
    const store = useReviewsStore();
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    store.regeneratingIds.add("another-review");
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".regenerate-btn").exists()).toBe(true);
    expect(wrapper.find(".regenerate-status").exists()).toBe(false);
  });

  it("puts the stored status back when asked after a failed change", async () => {
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });
    const select = wrapper.get(".modal-status-select");

    await select.setValue("Completed");
    (wrapper.vm as unknown as { resetStatus: () => void }).resetStatus();

    expect((select.element as HTMLSelectElement).value).toBe(draftReview.analysis_status);
  });

  it("closes from the close button", async () => {
    const wrapper = mount(ReviewDetailModal, { props: { open: true, review: draftReview } });

    await wrapper.get(".modal-close").trigger("click");

    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
