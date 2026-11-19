// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import HomeView from "@/views/HomeView.vue";

vi.mock("vue-router", () => ({ useRouter: () => ({ push: vi.fn() }) }));

vi.mock("@/services/reviewService", () => ({
  reviewService: { createReview: vi.fn() },
}));

describe("HomeView", () => {
  it("shows only the customer review form", () => {
    const wrapper = mount(HomeView);

    expect(wrapper.findAll("form.review-form")).toHaveLength(1);
    expect(wrapper.find(".case-card").exists()).toBe(false);
    expect(wrapper.find(".app-nav").exists()).toBe(true);
    expect(wrapper.find(".deck-arrow").exists()).toBe(false);
    expect(wrapper.find(".demo-card").exists()).toBe(false);
    wrapper.unmount();
  });
});
