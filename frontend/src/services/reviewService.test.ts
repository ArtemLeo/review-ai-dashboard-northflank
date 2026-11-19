// @vitest-environment jsdom
import { AxiosError, AxiosHeaders } from "axios";
import type { AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { afterEach, describe, expect, it } from "vitest";
import api from "@/services/api";
import { reviewService } from "@/services/reviewService";
import { AnalysisStatus } from "@/types";
import { extractErrorMessage } from "@/utils/errors";

const originalAdapter = api.defaults.adapter;

/** Answers every request with `data` and records the config the client sent. */
function respondWith(data: unknown): InternalAxiosRequestConfig[] {
  const sent: InternalAxiosRequestConfig[] = [];
  api.defaults.adapter = (config: InternalAxiosRequestConfig) => {
    sent.push(config);
    const response: AxiosResponse = { data, status: 200, statusText: "OK", headers: {}, config };
    return Promise.resolve(response);
  };
  return sent;
}

describe("api client", () => {
  it("sends the session cookie and the CSRF header the backend expects", () => {
    // The names match CSRF_COOKIE_NAME and CSRF_HEADER_NAME in
    // backend/app/core/security.py; a mismatch turns every change into a 403.
    expect(api.defaults.baseURL).toBe("/api");
    expect(api.defaults.withCredentials).toBe(true);
    expect(api.defaults.xsrfCookieName).toBe("XSRF-TOKEN");
    expect(api.defaults.xsrfHeaderName).toBe("X-XSRF-TOKEN");
  });
});

describe("reviewService", () => {
  afterEach(() => {
    api.defaults.adapter = originalAdapter;
  });

  it("changes a status with a PATCH of the status field", async () => {
    const sent = respondWith({});

    await reviewService.updateReviewStatus("review-1", AnalysisStatus.Completed);

    expect(sent[0].method).toBe("patch");
    expect(sent[0].url).toBe("/admin/reviews/review-1/status");
    expect(JSON.parse(String(sent[0].data))).toEqual({ analysis_status: "Completed" });
  });

  it("downloads the CSV export as a file, with the active filters", async () => {
    const sent = respondWith(new Blob(["id\n"]));

    await reviewService.exportReviews({ status: AnalysisStatus.Pending });

    expect(sent[0].method).toBe("get");
    expect(sent[0].url).toBe("/admin/reviews/export");
    expect(sent[0].responseType).toBe("blob");
    expect(sent[0].params).toMatchObject({ format: "csv", status: "Pending" });
  });

  it("shows the backend's message when the CSV export fails", async () => {
    // A failed download comes back as a Blob too, not as parsed JSON.  jsdom
    // lacks Blob.text(), which every browser has, so the test supplies it.
    const json = JSON.stringify({ detail: "The database is temporarily unavailable." });
    const body = Object.assign(new Blob([json], { type: "application/json" }), {
      text: () => Promise.resolve(json),
    });
    api.defaults.adapter = (config: InternalAxiosRequestConfig) =>
      Promise.reject(
        new AxiosError("Request failed", "ERR_BAD_RESPONSE", config, null, {
          status: 503,
          statusText: "",
          headers: {},
          config: { ...config, headers: new AxiosHeaders() },
          data: body,
        })
      );

    const error = await reviewService.exportReviews().catch((caught: unknown) => caught);

    expect(extractErrorMessage(error)).toBe("The database is temporarily unavailable.");
  });
});
