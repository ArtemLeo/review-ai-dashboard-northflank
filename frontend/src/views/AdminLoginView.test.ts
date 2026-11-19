// @vitest-environment jsdom
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/stores/auth";
import { apiError } from "@/test/fixtures";
import AdminLoginView from "@/views/AdminLoginView.vue";

const { push, replace } = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("vue-router", () => ({ useRouter: () => ({ push, replace }) }));

describe("AdminLoginView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => vi.useRealTimers());

  it("fills in the admin login", () => {
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });
    expect((wrapper.get("#email").element as HTMLInputElement).value).toBe("admin-artem-leo");
    expect((wrapper.get("#password").element as HTMLInputElement).value).toBe("password-artem-leo");
    wrapper.unmount();
  });

  it("does not redirect when a login request finishes after leaving the page", async () => {
    vi.useFakeTimers();
    let finishLogin: () => void = () => {};
    vi.spyOn(useAuthStore(), "login").mockImplementation(
      () =>
        new Promise((resolve) => {
          finishLogin = resolve;
        })
    );
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });
    await wrapper.get("form").trigger("submit");
    wrapper.unmount();

    finishLogin();
    await flushPromises();
    await vi.advanceTimersByTimeAsync(1000);

    expect(push).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("signs in, then puts the dashboard in place of the login page", async () => {
    vi.useFakeTimers();
    vi.spyOn(useAuthStore(), "login").mockResolvedValue(undefined);
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.find(".success").exists()).toBe(true);
    expect(replace).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(800);

    expect(replace).toHaveBeenCalledWith("/admin");
    expect(push).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it.each([
    [401, "Invalid login or password"],
    [429, "Too many failed sign-in attempts. Please wait a few minutes and try again"],
  ])("shows the server's message for an answer of %i", async (status, detail) => {
    vi.spyOn(useAuthStore(), "login").mockRejectedValue(apiError(status, detail));
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.get(".error").text()).toContain(detail);
    expect(replace).not.toHaveBeenCalled();
  });

  it("disables the button while the sign-in request runs", async () => {
    let fail: (error: unknown) => void = () => {};
    vi.spyOn(useAuthStore(), "login").mockImplementation(
      () =>
        new Promise((_resolve, reject) => {
          fail = reject;
        })
    );
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });
    const button = wrapper.get("button[type='submit']");

    await wrapper.get("form").trigger("submit");
    expect(button.attributes("disabled")).toBeDefined();
    expect(button.text()).toBe("Authenticating ...");

    fail(apiError(401, "Invalid login or password"));
    await flushPromises();

    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("shows and hides the password", async () => {
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });
    const field = wrapper.get("#password");
    const toggle = wrapper.get(".password-toggle");

    expect(field.attributes("type")).toBe("password");
    await toggle.trigger("click");
    expect(field.attributes("type")).toBe("text");
    // A toggle keeps its name; its pressed state tells whether it is on.
    expect(toggle.attributes("aria-label")).toBe("Show password");
    expect(toggle.attributes("aria-pressed")).toBe("true");
    await toggle.trigger("click");
    expect(field.attributes("type")).toBe("password");
  });

  it("keeps the browser's required-field validation", () => {
    const wrapper = mount(AdminLoginView, { global: { stubs: ["AboutModal"] } });

    expect(wrapper.get("form").attributes("novalidate")).toBeUndefined();
    expect(wrapper.get("#email").attributes("required")).toBeDefined();
    expect(wrapper.get("#password").attributes("required")).toBeDefined();
  });
});
