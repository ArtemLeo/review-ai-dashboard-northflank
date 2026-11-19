<template>
  <Transition name="modal">
    <div v-if="open" class="modal-overlay" @mousedown="onOverlayPress" @click="onOverlayClick">
      <div
        ref="panel"
        class="modal"
        :class="modalClass"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :lang="lang"
        tabindex="-1"
        @keydown.tab="trapFocus"
      >
        <div class="modal-header">
          <div class="modal-heading">
            <h2 :id="titleId" class="modal-title">{{ title }}</h2>
            <span v-if="subtitle" class="modal-meta">{{ subtitle }}</span>
          </div>
          <div class="modal-actions">
            <slot name="actions" />
            <button class="modal-close" :aria-label="closeLabel" @click="emit('close')">✕</button>
          </div>
        </div>
        <slot />
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
/**
 * Base modal dialog shared by every dialog of the app.
 *
 * The component owns the overlay, the header and the open/close transition so
 * that every dialog shares the same markup and animation.
 *
 * It also owns the keyboard behaviour of a modal dialog: the focus moves
 * into the dialog when it opens, Tab cycles inside it, Escape closes it, and
 * the focus returns to the control that opened it.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { isTopDialog, pushDialog, removeDialog } from "@/utils/modalStack";

const props = withDefaults(
  defineProps<{
    /** Whether the dialog is visible. */
    open: boolean;
    /** Dialog heading. */
    title: string;
    /** Optional secondary line rendered under the heading. */
    subtitle?: string;
    /** Extra class applied to the dialog panel. */
    modalClass?: string;
    /** Language of the dialog content, for screen readers. */
    lang?: string;
    /** Accessible name of the close button, in the dialog's language. */
    closeLabel?: string;
    /** Whether a click on the backdrop dismisses the dialog. */
    closeOnBackdrop?: boolean;
  }>(),
  {
    subtitle: "",
    modalClass: undefined,
    lang: undefined,
    closeLabel: "Close",
    closeOnBackdrop: true,
  }
);

const emit = defineEmits<{
  /** Emitted when the dialog should be dismissed. */
  close: [];
}>();

/** Identity of this dialog in the stack of open dialogs. */
const dialogId = Symbol("dialog");

/** Whether the mouse button went down on the backdrop itself. */
let pressedOnBackdrop = false;

function onOverlayPress(event: MouseEvent): void {
  pressedOnBackdrop = event.target === event.currentTarget;
}

/**
 * A click on the backdrop dismisses the dialog.  Selecting text inside the
 * panel and letting go over the backdrop also ends in a click there, so the
 * press has to start on the backdrop as well.
 */
function onOverlayClick(event: MouseEvent): void {
  if (props.closeOnBackdrop && pressedOnBackdrop && event.target === event.currentTarget) {
    emit("close");
  }
  pressedOnBackdrop = false;
}

/** Escape dismisses the dialog — only the top-most one when several are open. */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && props.open && isTopDialog(dialogId)) emit("close");
}

const panel = ref<HTMLElement | null>(null);
const titleId = `modal-title-${useId()}`;

/** The control that had the focus before the dialog opened. */
let returnFocusTo: HTMLElement | null = null;

const FOCUSABLE =
  'a[href], button:not([disabled]), select:not([disabled]), textarea:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Keeps Tab and Shift+Tab inside the dialog. */
function trapFocus(event: KeyboardEvent): void {
  const focusable = panel.value
    ? Array.from(panel.value.querySelectorAll<HTMLElement>(FOCUSABLE))
    : [];
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && (active === first || active === panel.value)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      pushDialog(dialogId);
      returnFocusTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      await nextTick();
      panel.value?.focus();
    } else {
      removeDialog(dialogId);
      returnFocusTo?.focus();
      returnFocusTo = null;
    }
  },
  { immediate: true }
);

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  removeDialog(dialogId);
});
</script>

<style scoped>
/* The overlay dims the dashboard with a soft vignette instead of a flat
   black sheet, so the panel behind it keeps a hint of depth. */
.modal-overlay {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(1200px 620px at 50% -10%, rgba(12, 17, 26, 0.72), transparent 70%),
    rgba(5, 8, 13, 0.78);
  backdrop-filter: blur(6px) saturate(110%);
  -webkit-backdrop-filter: blur(6px) saturate(110%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1.5rem;
}

/* The panel is a raised surface in the same dark family as the dashboard
   header, the toolbar and the table. */
.modal {
  position: relative;
  background: linear-gradient(180deg, #1b2231 0%, #131926 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow:
    0 44px 90px -24px rgba(0, 0, 0, 0.78),
    0 22px 44px -18px rgba(0, 0, 0, 0.62),
    0 3px 10px -2px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  width: 100%;
  max-width: 680px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* The panel receives the focus itself; the ring belongs to its controls. */
.modal:focus {
  outline: none;
}

.modal-header {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

/* Variant used by the statistics dialog */
.statistics-modal {
  align-items: center;
}

.statistics-modal .modal-header {
  max-width: 650px;
}

.modal-heading {
  min-width: 0;
}

/* Optional header controls sit on the title line, right before the close button. */
.modal-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.modal-title {
  font-family: "Rajdhani", sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  text-shadow: 0 2px 12px rgba(245, 158, 11, 0.18);
}

.modal-meta {
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 0.25rem;
  display: block;
}

/* The close button wears the red family of the logout button, so every
   way out of a dialog is easy to spot. */
.modal-close {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.22) 0%, rgba(239, 68, 68, 0.12) 100%);
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: 6px;
  color: #fecaca;
  cursor: pointer;
  font-size: 1rem;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.modal-close:hover {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.34) 0%, rgba(239, 68, 68, 0.2) 100%);
  border-color: rgba(239, 68, 68, 0.45);
  color: #fee2e2;
  box-shadow:
    0 4px 12px -2px rgba(239, 68, 68, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* Modal open/close animation */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .modal,
.modal-leave-active .modal {
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: translateY(-12px);
  opacity: 0;
}
</style>
