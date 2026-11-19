/**
 * Stack of the dialogs that are open right now, the top-most last.
 *
 * Every dialog listens for Escape on the window; only the one on top of the
 * stack reacts, so Escape never closes two dialogs at once.
 */
const openDialogs: symbol[] = [];

/** Puts a dialog on top of the stack. */
export function pushDialog(id: symbol): void {
  removeDialog(id);
  openDialogs.push(id);
}

/** Takes a dialog off the stack, wherever it is. */
export function removeDialog(id: symbol): void {
  const index = openDialogs.indexOf(id);
  if (index !== -1) openDialogs.splice(index, 1);
}

/** Whether the dialog is the top-most open one. */
export function isTopDialog(id: symbol): boolean {
  return openDialogs[openDialogs.length - 1] === id;
}

/**
 * Moves the focus from a control that is about to disappear to its dialog.
 *
 * A focused element that is removed sends the focus to the page body, behind
 * the dialog; the dialog panel is focusable, so the focus stays inside it.
 */
export function keepFocusInDialog(control: EventTarget | null): void {
  if (control instanceof HTMLElement) {
    control.closest<HTMLElement>('[role="dialog"]')?.focus();
  }
}
