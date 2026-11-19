import { AxiosError, AxiosHeaders } from "axios";
import { AnalysisStatus } from "@/types";
import type { AdminReviewDto, PaginationState } from "@/types";

/** An axios error carrying the backend's readable message. */
export function apiError(status: number, detail: string): AxiosError {
  const headers = new AxiosHeaders();
  return new AxiosError("Request failed", "ERR_BAD_RESPONSE", undefined, undefined, {
    status,
    statusText: "",
    headers,
    config: { headers },
    data: { detail },
  });
}

/** Builds an admin review with sensible defaults. */
export function makeReview(overrides: Partial<AdminReviewDto> = {}): AdminReviewDto {
  return {
    id: "review-1",
    author_name: "Test User",
    email: "test@example.com",
    text: "The app crashes on start.",
    language_code: "en",
    created_at_utc: "2026-10-22T10:00:00",
    analysis_status: AnalysisStatus.Pending,
    rating: null,
    priority: null,
    category: null,
    needs_urgent_response: null,
    ai_analysis_provider: null,
    ai_analysis_model: null,
    ai_draft_response: null,
    ai_draft_response_provider: null,
    ai_draft_response_model: null,
    analyzed_at_utc: null,
    ...overrides,
  };
}

/** Pagination state of a single full page. */
export function makePagination(overrides: Partial<PaginationState> = {}): PaginationState {
  return {
    currentPage: 1,
    totalPages: 1,
    rangeStart: 1,
    rangeEnd: 1,
    total: 1,
    ...overrides,
  };
}
