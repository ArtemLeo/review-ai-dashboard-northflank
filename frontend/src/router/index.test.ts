// @vitest-environment jsdom
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { SESSION_EXPIRED_EVENT } from "@/services/api";
import { useAuthStore } from "@/stores/auth";

vi.mock("@/services/authService", () => ({
  authService: {
    fetchSession: vi.fn().mockRejectedValue(new Error("401")),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

describe("router", () => {
  it("returns to the login page when the server rejects the session", async () => {
    setActivePinia(createPinia());
    const { default: router } = await import("@/router");
    const auth = useAuthStore();
    auth.isAuthenticated = true;
    auth.sessionChecked = true;
    await router.push({ name: "admin-dashboard" });
    await router.isReady();

    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    // The login page is a lazy chunk; its first, cold compilation on a busy
    // runner can take longer than the default second.
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe("admin-login"), {
      timeout: 5000,
    });

    expect(auth.isAuthenticated).toBe(false);
  });

  it("sends a signed-out visitor from the dashboard to the login page", async () => {
    setActivePinia(createPinia());
    const { default: router } = await import("@/router");
    await router.push({ name: "home" });

    await router.push({ name: "admin-dashboard" });

    expect(router.currentRoute.value.name).toBe("admin-login");
  });

  it("sends a signed-in admin from the login page to the dashboard", async () => {
    setActivePinia(createPinia());
    const { default: router } = await import("@/router");
    await router.push({ name: "home" });
    const auth = useAuthStore();
    auth.isAuthenticated = true;
    auth.sessionChecked = true;

    await router.push({ name: "admin-login" });

    expect(router.currentRoute.value.name).toBe("admin-dashboard");
  });

  it("leads an unknown address to the home page", async () => {
    setActivePinia(createPinia());
    const { default: router } = await import("@/router");

    await router.push("/no-such-page");

    expect(router.currentRoute.value.name).toBe("home");
  });

  it("does not ask for a session on the public home page", async () => {
    setActivePinia(createPinia());
    const { default: router } = await import("@/router");
    const { authService } = await import("@/services/authService");
    vi.mocked(authService.fetchSession).mockClear();

    await router.push({ name: "home" });

    expect(authService.fetchSession).not.toHaveBeenCalled();
    expect(useAuthStore().sessionChecked).toBe(false);
  });
});
