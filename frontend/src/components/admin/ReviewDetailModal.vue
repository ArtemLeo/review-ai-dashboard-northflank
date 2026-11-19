<template>
  <BaseModal
    :open="open"
    :title="review?.author_name ?? ''"
    :subtitle="subtitle"
    @close="emit('close')"
  >
    <template v-if="review">
      <div class="modal-badges">
        <span v-if="review.priority" :class="['badge', 'priority', review.priority.toLowerCase()]">
          {{ review.priority }}
        </span>
        <span
          v-if="review.rating"
          class="star-rating"
          role="img"
          :aria-label="`${review.rating} of 5 stars`"
          >{{ renderStars(review.rating) }}</span
        >
        <select
          ref="statusSelect"
          aria-label="Review status"
          class="modal-status-select"
          :value="review.analysis_status"
          @change="onStatusChange"
        >
          <option value="Pending">Pending</option>
          <option value="Processing">Processing</option>
          <option value="Completed">Completed</option>
        </select>
      </div>

      <div class="modal-section user-section">
        <div class="modal-section-label">
          <span class="section-icon" aria-hidden="true">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </span>
          <span>User Review</span>
        </div>
        <div class="modal-text">
          <button
            class="modal-field-copy-btn"
            :class="{ copied: copiedField === 'review' }"
            :aria-label="copiedField === 'review' ? 'Copied' : 'Copy review text'"
            @click="copy('review', review.text)"
          >
            <svg
              v-if="copiedField === 'review'"
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.6"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <svg
              v-else
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span v-if="copiedField === 'review'" class="copy-feedback" aria-hidden="true"
              >Copied!</span
            >
          </button>
          <p class="modal-review-text" :lang="review.language_code ?? undefined">
            {{ review.text }}
          </p>
        </div>
      </div>

      <template v-if="review.ai_draft_response">
        <div class="modal-section ai-section">
          <div class="modal-section-label">
            <span class="section-icon" aria-hidden="true">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="2" y="4" width="20" height="12" rx="2"></rect>
                <circle cx="7" cy="8" r="1"></circle>
                <circle cx="17" cy="8" r="1"></circle>
                <line x1="7" y1="4" x2="7" y2="2"></line>
                <line x1="17" y1="4" x2="17" y2="2"></line>
                <line x1="9" y1="14" x2="15" y2="14"></line>
              </svg>
            </span>
            <span>AI Response</span>
            <span
              v-if="regenerating"
              class="regenerate-status"
              role="status"
              aria-label="Generating another draft"
            >
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </span>
            <button
              v-if="!regenerating"
              class="regenerate-btn"
              aria-label="Generate another draft"
              data-hint="Generate another draft"
              @click="regenerateDraft"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path
                  d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
                ></path>
              </svg>
            </button>
          </div>
          <div class="modal-draft">
            <button
              class="modal-field-copy-btn"
              :class="{ copied: copiedField === 'draft' }"
              :aria-label="copiedField === 'draft' ? 'Copied' : 'Copy AI response'"
              @click="copy('draft', review.ai_draft_response ?? '')"
            >
              <svg
                v-if="copiedField === 'draft'"
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.6"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <svg
                v-else
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span v-if="copiedField === 'draft'" class="copy-feedback" aria-hidden="true"
                >Copied!</span
              >
            </button>
            <p :lang="review.language_code ?? undefined">{{ review.ai_draft_response }}</p>
          </div>
        </div>
      </template>

      <div v-if="review.ai_analysis_provider" class="modal-footer-meta">
        <template v-if="review.ai_analysis_provider === 'Automated Test Dataset'">
          Automated Test Dataset · Simulated Analysis
        </template>
        <template v-else>
          Analysis by {{ review.ai_analysis_provider }} · {{ review.ai_analysis_model }}
        </template>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import BaseModal from "@/components/admin/BaseModal.vue";
import { useReviewsStore } from "@/stores/reviews";
import type { AdminReviewDto, AnalysisStatus } from "@/types";
import { copyToClipboard, formatDate, renderStars } from "@/utils/format";
import { keepFocusInDialog } from "@/utils/modalStack";

/** Full details of a single review. */
const props = defineProps<{
  /** Whether the dialog is visible. */
  open: boolean;
  /** Review being displayed, or null when the dialog is closed. */
  review: AdminReviewDto | null;
}>();

/** Pinia store that tells which reviews have a draft being regenerated. */
const reviewsStore = useReviewsStore();

/** The spinner belongs to the review whose draft is being regenerated. */
const regenerating = computed(
  () => props.review !== null && reviewsStore.regeneratingIds.has(props.review.id)
);

const emit = defineEmits<{
  /** Emitted when the dialog should be dismissed. */
  close: [];
  /** Emitted with the newly selected analysis status. */
  "update-status": [status: AnalysisStatus];
  /** Emitted when the AI draft should be regenerated. */
  "regenerate-draft": [];
}>();

/** Secondary header line combining the author email and submission date. */
const subtitle = computed(() =>
  props.review ? `${props.review.email} · ${formatDate(props.review.created_at_utc)}` : ""
);

function onStatusChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value as AnalysisStatus;
  emit("update-status", value);
}

const statusSelect = ref<HTMLSelectElement | null>(null);

/**
 * Shows the stored status in the select again, after the server refused a
 * change.  The prop did not change, so Vue would not reset the select itself;
 * doing it in place keeps the dialog, its focus and its scroll position.
 */
function resetStatus(): void {
  if (statusSelect.value && props.review) statusSelect.value.value = props.review.analysis_status;
}

defineExpose({ resetStatus });

/** Field whose text was just copied; its button shows a check mark. */
const copiedField = ref<"review" | "draft" | null>(null);
let copiedTimer: ReturnType<typeof setTimeout> | null = null;

/** How long the "Copied!" confirmation stays on the button. */
const COPIED_FEEDBACK_MS = 1800;

async function copy(field: "review" | "draft", text: string): Promise<void> {
  if (!(await copyToClipboard(text))) return;
  copiedField.value = field;
  if (copiedTimer !== null) clearTimeout(copiedTimer);
  copiedTimer = setTimeout(() => {
    copiedField.value = null;
  }, COPIED_FEEDBACK_MS);
}

onBeforeUnmount(() => {
  if (copiedTimer !== null) clearTimeout(copiedTimer);
});

/**
 * Asks the parent to regenerate the AI draft response for this review.
 * The parent owns the request, so a click triggers exactly one AI call.
 *
 * The button gives way to the loading dots, so the focus moves to the dialog
 * first; otherwise it would fall out of the dialog with the removed button.
 */
function regenerateDraft(event: MouseEvent): void {
  keepFocusInDialog(event.currentTarget);
  emit("regenerate-draft");
}
</script>

<style scoped>
.modal-badges {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding-bottom: 1rem;
  margin-bottom: 0.5rem;
}

.modal-status-select {
  padding: 0.4rem 2.5rem 0.4rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  font-size: 0.8rem;
  font-family: "Rajdhani", sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  background-color: rgba(8, 11, 17, 0.6);
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><path fill="%23a0aec0" d="M6 9L1 4h10z"/></svg>');
  background-repeat: no-repeat;
  background-position: right 0.9rem center;
  color: #f1f5f9;
  cursor: pointer;
  transition: all 0.2s ease;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  box-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.45),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
}

.modal-status-select:hover {
  border-color: var(--ice-border);
}

.modal-status-select:focus {
  outline: none;
  border-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
}

.modal-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

/* The AI Response label and its draft panel need a bit more breathing room
   than the review text panel — the regenerate button sits right after the
   label, so the draft below it should start a full 1rem lower. */
.ai-section .modal-draft {
  margin-top: 0.4rem;
}

/* Extra spacing before the AI Response section, on top of the default gap. */
.modal-section + .modal-section {
  margin-top: 1rem;
}

.modal-section-label {
  font-family: "Rajdhani", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #a8b3c4;
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

/* Section icons are rounded-square avatar badges, not buttons: a dark tile
   with an amber line icon, so they never read as clickable controls. */
.section-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 9px;
  flex-shrink: 0;
  background: #1e293b;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.section-icon svg {
  width: 21px;
  height: 21px;
}

/* Regenerate button sits right after the AI Response label — same amber
   family as the toolbar tool buttons, but icon-only. */
.regenerate-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border-radius: 50%;
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  border: none;
  cursor: pointer;
  color: #1c1305;
  transition: all 0.2s ease;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.regenerate-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, #fcd34d 0%, #f59e0b 58%, #e08e05 100%);
  transform: translateY(-1px);
  box-shadow:
    0 8px 18px -4px rgba(245, 158, 11, 0.35),
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

/* Hover hint above the button, styled like the "Click to view full
   details" hint of the review table, with the same reading delay. */
.regenerate-btn {
  position: relative;
}

.regenerate-btn::after {
  content: attr(data-hint);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: #1c2434;
  color: #fbbf24;
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  font-family: "Inter", sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.4px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  z-index: 20;
  border: 1px solid rgba(245, 158, 11, 0.25);
  box-shadow:
    0 2px 8px -2px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: opacity 0.2s ease;
}

.regenerate-btn:hover::after {
  opacity: 1;
  transition-delay: 1000ms;
}

/* Loading dots shown in place of the button while a draft is being regenerated. */
.regenerate-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  gap: 3px;
  color: #f59e0b;
}

.regenerate-status .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: regenerate-bounce 1.4s ease-in-out infinite both;
}

.regenerate-status .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.regenerate-status .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes regenerate-bounce {
  0%,
  80%,
  100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.user-section .section-icon {
  color: #fbbf24;
}

.ai-section .section-icon {
  color: #f59e0b;
}

.modal-field-copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
  position: absolute;
  top: 0.6rem;
  right: 0.6rem;
  opacity: 0;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.4);
}

.modal-text:hover .modal-field-copy-btn,
.modal-draft:hover .modal-field-copy-btn,
.modal-field-copy-btn:focus-visible {
  opacity: 1;
}

/* Touch screens have no hover, so the copy buttons are always shown there. */
@media (hover: none) {
  .modal-field-copy-btn {
    opacity: 1;
  }
}

.modal-field-copy-btn:hover {
  background: var(--ice-bg);
  border-color: var(--ice-border);
  color: var(--ice-text);
  box-shadow: 0 2px 8px -2px var(--ice-glow);
}

/* Copy confirmation: the icon turns into a green check mark and a small
   "Copied!" label appears beside it for a moment. */
.modal-field-copy-btn.copied,
.modal-field-copy-btn.copied:hover {
  opacity: 1;
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.5);
  color: #6ee7b7;
  box-shadow: 0 2px 8px -2px rgba(16, 185, 129, 0.35);
}

/* Shown above the copy button, so it never covers the text being copied. */
.copy-feedback {
  position: absolute;
  right: 0;
  bottom: calc(100% + 6px);
  padding: 0.15rem 0.5rem;
  border-radius: 5px;
  background: #0f2a22;
  border: 1px solid rgba(16, 185, 129, 0.45);
  color: #6ee7b7;
  font-family: "Inter", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
  animation: copied-in 0.15s ease;
}

@keyframes copied-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

/* The review text is recessed into the panel, the AI answer is a raised
   green surface — the same in/out logic as the dashboard inputs. */
.modal-text {
  background: rgba(8, 11, 17, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  padding: 1rem 2.5rem 1rem 1.25rem;
  color: #e2e8f0;
  font-size: 0.95rem;
  line-height: 1.65;
  word-break: break-word;
  position: relative;
  box-shadow:
    inset 0 1px 4px rgba(0, 0, 0, 0.5),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
}

/* The review keeps its own line breaks.  The pre-wrap mode lives on the
   paragraph, not on the panel, so the whitespace of the template around it
   stays collapsed and the first character starts at the left edge. */
.modal-review-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.modal-draft {
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.13) 0%, rgba(16, 185, 129, 0.04) 100%);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 8px;
  padding: 1rem 2.5rem 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
  box-shadow:
    0 8px 18px -8px rgba(16, 185, 129, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.modal-draft p {
  color: #6ee7b7;
  font-size: 0.95rem;
  line-height: 1.65;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.modal-footer-meta {
  font-size: 0.78rem;
  color: #94a3b8;
  font-family: "Inter", sans-serif;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  padding-top: 1rem;
  margin-top: 1.3rem;
}
</style>
