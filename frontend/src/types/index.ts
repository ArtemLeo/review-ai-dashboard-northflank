/** Shared TypeScript types mirroring the backend Pydantic schemas. */

/** Handling status of a review, managed by the support operator. */
export enum AnalysisStatus {
  Pending = "Pending",
  Processing = "Processing",
  Completed = "Completed",
}

/** Star rating for customer reviews (1-5 stars). */
export type Rating = 1 | 2 | 3 | 4 | 5;

/** Urgency / business priority of a review. */
export enum Priority {
  Low = "Low",
  Medium = "Medium",
  High = "High",
}

/** Categorization domain for feedback. */
enum ReviewCategory {
  Praise = "Praise",
  FeatureRequest = "FeatureRequest",
  Bug = "Bug",
  PaymentIssue = "PaymentIssue",
  Support = "Support",
  Other = "Other",
}

/** Fields the admin review list is allowed to sort by. */
type SortField = "created_at_utc" | "rating" | "priority";

/** Fields accepted by the public review form. */
export interface CreateReviewRequest {
  author_name: string;
  email: string;
  text: string;
}

/**
 * Public review representation.
 * The public endpoints deliberately omit the author's email address.
 */
export interface ReviewDto {
  id: string;
  author_name: string;
  text: string;
  language_code: string | null;
  created_at_utc: string;
  analysis_status: AnalysisStatus;
  rating: Rating | null;
  priority: Priority | null;
  category: ReviewCategory | null;
  needs_urgent_response: boolean | null;
  ai_analysis_provider: string | null;
  ai_analysis_model: string | null;
  ai_draft_response: string | null;
  ai_draft_response_provider: string | null;
  ai_draft_response_model: string | null;
  analyzed_at_utc: string | null;
}

/** Full review representation, including the author's email (admin area only). */
export interface AdminReviewDto extends ReviewDto {
  email: string;
}

/** Credentials accepted by the login endpoint. */
export interface LoginInput {
  email: string;
  password: string;
}

/** The signed-in administrator, as reported by the session endpoints. */
export interface AdminSession {
  email: string;
}

/** Filter and sorting parameters for the admin review list. */
export interface ReviewQuery {
  status?: AnalysisStatus;
  rating?: Rating;
  priority?: Priority;
  sort_by?: SortField;
  descending?: boolean;
  page?: number;
  page_size?: number;
}

/** Paginated list response returned by the admin reviews endpoint. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** Ratings distribution reported by the admin statistics endpoint. */
export interface ReviewStatistics {
  rating_1: number;
  rating_2: number;
  rating_3: number;
  rating_4: number;
  rating_5: number;
  total: number;
  avg_rating: number;
}

/** Filter controls shown above the review table. */
export type ReviewFilterField = "status" | "rating" | "priority";

/** Everything the pagination bar needs to render the current page. */
export interface PaginationState {
  currentPage: number;
  totalPages: number;
  rangeStart: number;
  rangeEnd: number;
  total: number;
}
