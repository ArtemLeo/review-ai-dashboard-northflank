import { describe, expect, it } from "vitest";
import { pageRange } from "@/utils/pagination";

describe("pageRange", () => {
  it("is empty without reviews", () => {
    expect(pageRange(1, 10, 0)).toEqual({ start: 0, end: 0 });
  });

  it("covers a full page", () => {
    expect(pageRange(2, 10, 101)).toEqual({ start: 11, end: 20 });
  });

  it("stops at the total on the last page", () => {
    expect(pageRange(11, 10, 101)).toEqual({ start: 101, end: 101 });
  });
});
