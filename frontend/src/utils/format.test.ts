import { describe, expect, it } from "vitest";
import { formatDate, formatShortDate, renderStars } from "@/utils/format";

describe("renderStars", () => {
  it("returns an empty string without a rating", () => {
    expect(renderStars(null)).toBe("");
  });

  it("fills the given number of stars out of five", () => {
    expect(renderStars(3)).toBe("★★★☆☆");
    expect(renderStars(5)).toBe("★★★★★");
  });

  it("clamps a rating outside the 1-5 range instead of throwing", () => {
    expect(renderStars(9)).toBe("★★★★★");
    expect(renderStars(0.4)).toBe("★☆☆☆☆");
  });
});

describe("formatDate", () => {
  it("shows a dash for a missing value", () => {
    expect(formatDate(null)).toBe("-");
  });

  it("returns an unparseable value unchanged", () => {
    expect(formatDate("not a date")).toBe("not a date");
  });

  it("treats a timestamp without an offset as UTC", () => {
    expect(formatDate("2026-10-22T10:00:00")).toBe(formatDate("2026-10-22T10:00:00Z"));
  });
});

describe("formatShortDate", () => {
  it("shows a dash for a missing value", () => {
    expect(formatShortDate(null)).toBe("-");
  });

  it("drops the year and uses a 24-hour clock", () => {
    const short = formatShortDate("2026-10-22T10:00:00Z");
    expect(short).not.toContain("2026");
    expect(short).not.toMatch(/AM|PM/);
  });
});
