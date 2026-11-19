// @vitest-environment jsdom
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { authService } from "@/services/authService";
import { useAuthStore } from "@/stores/auth";
import { useReviewsStore } from "@/stores/reviews";
import { makeReview } from "@/test/fixtures";

vi.mock("@/services/authService", () => ({
  authService: { login: vi.fn(), logout: vi.fn(), fetchSession: vi.fn() },
}));

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("keeps the session available for retry when server revocation fails", async () => {
    vi.mocked(authService.logout).mockRejectedValue(new Error("Revocation unavailable"));
    const reviews = useReviewsStore();
    reviews.reviews = [makeReview()];
    const auth = useAuthStore();
    auth.isAuthenticated = true;

    await expect(auth.logout()).rejects.toThrow("Revocation unavailable");

    expect(auth.isAuthenticated).toBe(true);
    expect(reviews.reviews).toHaveLength(1);
    vi.mocked(authService.logout).mockResolvedValue(undefined);
    await auth.logout();
    expect(auth.isAuthenticated).toBe(false);
    expect(reviews.reviews).toEqual([]);
  });

  it("forgets the loaded reviews on sign-out", async () => {
    vi.mocked(authService.logout).mockResolvedValue(undefined);
    const reviews = useReviewsStore();
    reviews.reviews = [makeReview()];
    const auth = useAuthStore();
    auth.isAuthenticated = true;

    await auth.logout();

    expect(auth.isAuthenticated).toBe(false);
    expect(reviews.reviews).toEqual([]);
  });

  it("forgets the loaded reviews when the session expires", () => {
    const reviews = useReviewsStore();
    reviews.reviews = [makeReview()];
    const auth = useAuthStore();

    auth.expireSession();

    expect(auth.sessionChecked).toBe(true);
    expect(reviews.reviews).toEqual([]);
  });
});
