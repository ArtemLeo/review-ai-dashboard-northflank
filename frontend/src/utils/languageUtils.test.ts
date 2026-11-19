import { describe, expect, it } from "vitest";
import { getLanguageFlag } from "@/utils/languageUtils";

describe("getLanguageFlag", () => {
  it("returns the flag of a known language, ignoring the case", () => {
    expect(getLanguageFlag("de")).toBe("🇩🇪");
    expect(getLanguageFlag("DE")).toBe("🇩🇪");
    expect(getLanguageFlag("uk")).toBe("🇺🇦");
    // The AI cannot tell US from British English, so English has one flag.
    expect(getLanguageFlag("en")).toBe("🇺🇸");
  });

  it("knows the rare languages a curious visitor may try", () => {
    expect(getLanguageFlag("kk")).toBe("🇰🇿");
    expect(getLanguageFlag("ka")).toBe("🇬🇪");
    expect(getLanguageFlag("pt")).toBe("🇵🇹");
    expect(getLanguageFlag("sw")).toBe("🇹🇿");
    expect(getLanguageFlag("la")).toBe("🇻🇦");
  });

  it("shows the country of a regional code", () => {
    expect(getLanguageFlag("en-US")).toBe("🇺🇸");
    expect(getLanguageFlag("pt-br")).toBe("🇧🇷");
    expect(getLanguageFlag("en-UK")).toBe("🇬🇧");
  });

  it("ignores a script subtag", () => {
    expect(getLanguageFlag("zh-Hans")).toBe("🇨🇳");
  });

  it("reads the deprecated codes some models still use", () => {
    expect(getLanguageFlag("iw")).toBe("🇮🇱");
    expect(getLanguageFlag("in")).toBe("🇮🇩");
  });

  it("returns a globe for a missing, unknown or constructed language", () => {
    expect(getLanguageFlag("xx")).toBe("🌐");
    expect(getLanguageFlag("eo")).toBe("🌐");
    expect(getLanguageFlag(null)).toBe("🌐");
  });
});
