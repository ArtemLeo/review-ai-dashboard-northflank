/** Pagination helpers for the admin review list. */

/**
 * Positions of the first and the last review shown on a page.
 *
 * @param page - The current page (1-based).
 * @param pageSize - The number of reviews per page.
 * @param total - The total number of reviews.
 * @returns The 1-based range, or `{ start: 0, end: 0 }` when there are no reviews.
 */
export function pageRange(
  page: number,
  pageSize: number,
  total: number
): { start: number; end: number } {
  if (total === 0) return { start: 0, end: 0 };
  return { start: (page - 1) * pageSize + 1, end: Math.min(page * pageSize, total) };
}
