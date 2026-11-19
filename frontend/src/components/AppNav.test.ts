// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import AppNav from "@/components/AppNav.vue";

const push = vi.fn();
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));

describe("AppNav", () => {
  it("links the home page to the admin panel", async () => {
    const wrapper = mount(AppNav, { props: { link: "admin" } });

    const link = wrapper.get("[aria-label='Admin Panel']");
    // A lock marks the way into the admin area.
    expect(link.find("svg rect").exists()).toBe(true);
    await link.trigger("click");

    expect(push).toHaveBeenCalledWith("/admin");
  });

  it("links the admin login page back to home", async () => {
    push.mockClear();
    const wrapper = mount(AppNav, { props: { link: "review" } });

    // The home icon marks the way back to the review form.
    expect(wrapper.get("[aria-label='Home Page'] svg").html()).toContain("M3 21h18");
    await wrapper.get("[aria-label='Home Page']").trigger("click");

    expect(push).toHaveBeenCalledWith("/");
  });

  it("asks for the About dialog", async () => {
    const wrapper = mount(AppNav, { props: { link: "admin" } });

    await wrapper.get("[aria-label='About Project']").trigger("click");

    expect(wrapper.emitted("about")).toHaveLength(1);
  });

  it("keeps the centre a plain product mark", () => {
    const wrapper = mount(AppNav, { props: { link: "review" } });

    const brand = wrapper.get(".brand");
    expect(brand.element.tagName).toBe("SPAN");
    expect(brand.find(".brand-logo").exists()).toBe(true);
    expect(brand.text()).toBe("CS2");
    expect(brand.find(".sparkles").exists()).toBe(false);
  });
});
