import axios from "axios";

/**
 * Extracts a human-readable message from an unknown catch value.
 *
 * The backend is the single source of truth for the wording of the API
 * errors: every 4xx response carries a human-readable message in
 * ``error.response.data.detail`` — a rate-limit notice for 429, a
 * per-field sentence for 422, a friendly hint for 401.  Only the cases the
 * backend cannot describe (server errors, network failures) get a message
 * from the frontend.
 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string" && detail.length > 0) {
      return detail;
    }

    switch (error.response?.status) {
      case 429:
        return "Too many requests. Please wait before trying again";
      case 500:
      case 502:
      case 503:
        return "Server error. Please try again later";
      default:
        break;
    }

    if (error.code === "ERR_NETWORK") {
      return "Network error. Please check your connection";
    }
    return "Something went wrong. Please try again later";
  }
  return "Something went wrong. Please try again later";
}
