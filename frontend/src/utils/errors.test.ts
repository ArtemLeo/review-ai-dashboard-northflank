import { AxiosError } from "axios";
import type { AxiosResponse } from "axios";
import { describe, expect, it } from "vitest";
import { extractErrorMessage } from "@/utils/errors";

/** Builds an Axios error that carries a response with the given status and body. */
function httpError(status: number, data: unknown): AxiosError {
  const response = { status, data } as AxiosResponse;
  return new AxiosError("request failed", "ERR_BAD_RESPONSE", undefined, undefined, response);
}

describe("extractErrorMessage", () => {
  it("prefers the message written by the backend", () => {
    expect(
      extractErrorMessage(httpError(422, { detail: "Email must be a valid email address" }))
    ).toBe("Email must be a valid email address");
  });

  it("describes a rate limit when the backend sent no message", () => {
    expect(extractErrorMessage(httpError(429, {}))).toBe(
      "Too many requests. Please wait before trying again"
    );
  });

  it("describes a server failure", () => {
    expect(extractErrorMessage(httpError(503, {}))).toBe("Server error. Please try again later");
  });

  it("describes a network failure", () => {
    expect(extractErrorMessage(new AxiosError("offline", "ERR_NETWORK"))).toBe(
      "Network error. Please check your connection"
    );
  });

  it("falls back to a generic message for anything else", () => {
    expect(extractErrorMessage(new Error("boom"))).toBe(
      "Something went wrong. Please try again later"
    );
  });
});
