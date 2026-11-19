// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StatisticsModal from "@/components/admin/StatisticsModal.vue";
import type { ReviewStatistics } from "@/types";

function makeStatistics(overrides: Partial<ReviewStatistics> = {}): ReviewStatistics {
  return {
    rating_1: 5,
    rating_2: 10,
    rating_3: 20,
    rating_4: 35,
    rating_5: 30,
    total: 100,
    avg_rating: 3.75,
    ...overrides,
  };
}

const emptyStatistics: ReviewStatistics = {
  rating_1: 0,
  rating_2: 0,
  rating_3: 0,
  rating_4: 0,
  rating_5: 0,
  total: 0,
  avg_rating: 0,
};

describe("StatisticsModal", () => {
  beforeEach(() => {
    let rafId = 0;
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      const id = ++rafId;
      cb(performance.now() + 3000);
      return id;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing while closed", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: false, statistics: makeStatistics(), loading: false, error: null },
    });

    expect(wrapper.find("[role='dialog']").exists()).toBe(false);
  });

  it("shows the dialog when open", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: makeStatistics(), loading: false, error: null },
    });

    expect(wrapper.find("[role='dialog']").exists()).toBe(true);
    expect(wrapper.get(".modal-title").text()).toBe("Review Statistics");
  });

  it("shows a loading spinner while loading", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: emptyStatistics, loading: true, error: null },
    });

    expect(wrapper.find(".loading").exists()).toBe(true);
    expect(wrapper.text()).toContain("Loading statistics...");
    expect(wrapper.find(".statistics-content").exists()).toBe(false);
  });

  it("shows an error message when there is an error", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: emptyStatistics, loading: false, error: "Network error" },
    });

    expect(wrapper.find(".error").exists()).toBe(true);
    expect(wrapper.text()).toContain("Network error");
    expect(wrapper.find(".statistics-content").exists()).toBe(false);
  });

  it("displays rating counts after animation completes", async () => {
    const stats = makeStatistics();
    const wrapper = mount(StatisticsModal, {
      props: { open: false, statistics: stats, loading: false, error: null },
    });

    await wrapper.setProps({ open: true });
    await nextTick();

    const values = wrapper.findAll(".stat-value").map((el) => el.text());
    expect(values).toEqual(["30", "35", "20", "10", "5"]);
  });

  it("displays the total and average rating", async () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: false, statistics: makeStatistics(), loading: false, error: null },
    });

    await wrapper.setProps({ open: true });
    await nextTick();

    expect(wrapper.text()).toContain("Total Reviews:");
    expect(wrapper.text()).toContain("100");
    expect(wrapper.text()).toContain("3.8");
  });

  it("renders five stat cards ordered from 5 stars to 1 star", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: makeStatistics(), loading: false, error: null },
    });

    const cards = wrapper.findAll(".stat-card");
    expect(cards).toHaveLength(5);
    expect(cards[0].classes()).toContain("rating-5");
    expect(cards[4].classes()).toContain("rating-1");
  });

  it("renders five progress bars", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: makeStatistics(), loading: false, error: null },
    });

    const bars = wrapper.findAll(".progress-item");
    expect(bars).toHaveLength(5);
  });

  it("handles zero reviews gracefully", async () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: false, statistics: emptyStatistics, loading: false, error: null },
    });

    await wrapper.setProps({ open: true });
    await nextTick();

    const values = wrapper.findAll(".stat-value").map((el) => el.text());
    expect(values).toEqual(["0", "0", "0", "0", "0"]);
    const percents = wrapper.findAll(".progress-value").map((el) => el.text());
    expect(percents).toEqual(["0.0%", "0.0%", "0.0%", "0.0%", "0.0%"]);
    expect(wrapper.get(".stats-total strong").text()).toBe("0");
    expect(wrapper.find(".rating-number").text()).toBe("0.0");
  });

  it("shows percentage values in progress bars", async () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: false, statistics: makeStatistics(), loading: false, error: null },
    });

    await wrapper.setProps({ open: true });
    await nextTick();

    // The bars run from 5 stars down to 1: 30, 35, 20, 10 and 5 of 100.
    const percents = wrapper.findAll(".progress-value").map((el) => el.text());
    expect(percents).toEqual(["30.0%", "35.0%", "20.0%", "10.0%", "5.0%"]);
  });

  it("closes from the close button", async () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: makeStatistics(), loading: false, error: null },
    });

    await wrapper.get(".modal-close").trigger("click");

    expect(wrapper.emitted("close")).toHaveLength(1);
  });

  it("provides aria-labels on star labels", () => {
    const wrapper = mount(StatisticsModal, {
      props: { open: true, statistics: makeStatistics(), loading: false, error: null },
    });

    const labels = wrapper.findAll(".stat-label");
    expect(labels[0].attributes("aria-label")).toBe("5 stars");
    expect(labels[4].attributes("aria-label")).toBe("1 star");
    expect(wrapper.findAll(".progress-label")[4].attributes("aria-label")).toBe("1 star");
  });
});
