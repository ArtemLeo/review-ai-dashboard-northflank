import axios from "axios";
import api from "./api";
import type {
  AdminReviewDto,
  AnalysisStatus,
  CreateReviewRequest,
  PaginatedResponse,
  ReviewStatistics,
  ReviewDto,
  ReviewQuery,
} from "@/types";

/**
 * Turns the Blob body of a failed download back into the JSON error the API
 * sent, so the backend's message reaches the user as for any other request.
 */
async function restoreJsonErrorBody(error: unknown): Promise<void> {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      error.response.data = JSON.parse(await error.response.data.text());
    } catch {
      // Not JSON (an HTML error page, for one): the generic message stays.
    }
  }
}

/** Review service — wraps all review-related API endpoints. */
export const reviewService = {
  /** Submits a new customer review and returns the created record. */
  async createReview(request: CreateReviewRequest): Promise<ReviewDto> {
    const response = await api.post<ReviewDto>("/reviews", request);
    return response.data;
  },

  /**
   * Fetches a page of the admin review list, applying optional filters and sorting.
   * The backend performs the pagination server-side.
   */
  async getReviews(query: ReviewQuery = {}): Promise<PaginatedResponse<AdminReviewDto>> {
    const response = await api.get<PaginatedResponse<AdminReviewDto>>("/admin/reviews", {
      params: {
        status: query.status,
        rating: query.rating,
        priority: query.priority,
        sort_by: query.sort_by,
        descending: query.descending,
        page: query.page,
        page_size: query.page_size,
      },
    });
    return response.data;
  },

  /** Updates the handling status of a review. */
  async updateReviewStatus(id: string, status: AnalysisStatus): Promise<AdminReviewDto> {
    const response = await api.patch<AdminReviewDto>(`/admin/reviews/${id}/status`, {
      analysis_status: status,
    });
    return response.data;
  },

  /** Regenerates the AI draft response for a review. */
  async regenerateDraftResponse(id: string): Promise<AdminReviewDto> {
    const response = await api.post<AdminReviewDto>(`/admin/reviews/${id}/regenerate-draft`);
    return response.data;
  },

  /** Fetches review statistics (ratings distribution). */
  async getStatistics(): Promise<ReviewStatistics> {
    const response = await api.get<ReviewStatistics>("/admin/reviews/statistics");
    return response.data;
  },

  /**
   * Downloads the review list as a CSV file.
   *
   * The response is read as a Blob, because the browser has to save it as a
   * file rather than parse it as JSON.
   */
  async exportReviews(query: ReviewQuery = {}): Promise<Blob> {
    try {
      const response = await api.get<Blob>("/admin/reviews/export", {
        params: {
          format: "csv",
          status: query.status,
          rating: query.rating,
          priority: query.priority,
          sort_by: query.sort_by,
          descending: query.descending,
        },
        responseType: "blob",
      });
      return response.data;
    } catch (error: unknown) {
      // A failed request also comes back as a Blob; restore its message.
      await restoreJsonErrorBody(error);
      throw error;
    }
  },
};
