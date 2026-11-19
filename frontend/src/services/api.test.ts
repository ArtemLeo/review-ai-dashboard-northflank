// @vitest-environment jsdom
import { AxiosError, AxiosHeaders } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import api, { SESSION_EXPIRED_EVENT } from "@/services/api";

/** Makes every request of the shared client fail with the given status. */
function failWith(status: number): void {
  api.defaults.adapter = (config: InternalAxiosRequestConfig) =>
    Promise.reject(
      new AxiosError("failed", "ERR_BAD_RESPONSE", config, null, {
        status,
        statusText: "",
        headers: {},
        config: { ...config, headers: new AxiosHeaders() },
        data: {},
      })
    );
}

describe("api 401 handling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("announces an expired session instead of reloading the page", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);
    failWith(401);

    await expect(api.get("/admin/reviews")).rejects.toThrow();

    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
  });

  it("leaves the 401 of a session probe to its caller", async () => {
    const listener = vi.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, listener);
    failWith(401);

    await expect(api.post("/auth/login")).rejects.toThrow();
    await expect(api.get("/auth/me")).rejects.toThrow();

    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener);
  });
});
