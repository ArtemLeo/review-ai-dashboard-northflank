/** Date formatting and presentation helpers shared across views. */

/**
 * Parse a timestamp returned by the API into a `Date`.
 *
 * The backend stores every timestamp as a naive UTC value and serialises
 * it without an offset, e.g. `2026-10-22T10:00:00`.  The JavaScript
 * `Date` constructor interprets a date-time string without an offset as
 * *local* time, so the browser would show a time shifted by the offset of
 * the visitor's own timezone.  The missing `Z` is added here to tell the
 * engine that the value is UTC.
 *
 * @param dateStr - The timestamp string received from the API.
 * @returns The parsed date, or `null` when the value cannot be parsed.
 */
function parseApiDate(dateStr: string): Date | null {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(dateStr);
  const normalized = hasTimezone ? dateStr : `${dateStr}Z`;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed;
}

/** Format an ISO-8601 UTC timestamp as a localized date string. */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const parsed = parseApiDate(dateStr);
  if (!parsed) return dateStr;
  return parsed.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a timestamp compactly for table cells, e.g. `Oct 28, 04:18`.
 * The full date with the year stays in the review dialog.
 */
export function formatShortDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const parsed = parseApiDate(dateStr);
  if (!parsed) return dateStr;
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}

/**
 * Render a 1–5 star string, without formatting if rating is absent.
 *
 * A rating outside the 1–5 range would make `String.repeat` throw, so the
 * value is clamped to the range first.
 *
 * @param rating - The star rating to render, or `null` when there is none.
 * @returns The filled and empty stars, or an empty string without a rating.
 */
export function renderStars(rating: number | null): string {
  if (!rating) return "";
  const clamped = Math.min(5, Math.max(1, Math.round(rating)));
  return "★".repeat(clamped) + "☆".repeat(5 - clamped);
}

/**
 * Copy text to the clipboard, falling back to a temporary textarea when needed.
 *
 * @returns `true` when the text reached the clipboard, so the caller confirms
 * the copy only when it really happened.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false;

  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Clipboard API rejected the request — fall back to the legacy path.
    }
  }

  const helper = document.createElement("textarea");
  helper.value = text;
  helper.setAttribute("readonly", "");
  helper.style.position = "fixed";
  helper.style.opacity = "0";
  document.body.appendChild(helper);
  helper.select();
  try {
    return document.execCommand("copy");
  } catch {
    // Clipboard is unavailable in this context — nothing else can be done.
    return false;
  } finally {
    document.body.removeChild(helper);
  }
}
