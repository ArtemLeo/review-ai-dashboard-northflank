import { defineStore } from "pinia";
import { ref } from "vue";
import { authService } from "@/services/authService";
import { useReviewsStore } from "@/stores/reviews";
import type { LoginInput } from "@/types";

/** Pinia store for authentication state and session management. */
export const useAuthStore = defineStore("auth", () => {
  /** True once the server has confirmed a session for this page load. */
  const isAuthenticated = ref(false);

  /** True after the first session check, so the guard asks the server only once. */
  const sessionChecked = ref(false);

  /** Logs in the user; the session cookie is stored by the browser. */
  async function login(input: LoginInput): Promise<void> {
    await authService.login(input);
    isAuthenticated.value = true;
    sessionChecked.value = true;
  }

  /**
   * Asks the server whether the browser holds a valid session.
   * A missing or expired session is a normal answer, not an error.
   */
  async function restoreSession(): Promise<void> {
    try {
      await authService.fetchSession();
      isAuthenticated.value = true;
    } catch {
      isAuthenticated.value = false;
    } finally {
      sessionChecked.value = true;
    }
  }

  /** Clears the local session only after the server confirms revocation. */
  async function logout(): Promise<void> {
    await authService.logout();
    isAuthenticated.value = false;
    useReviewsStore().clear();
  }

  /** Forgets a session the server no longer accepts (an answer of HTTP 401). */
  function expireSession(): void {
    isAuthenticated.value = false;
    sessionChecked.value = true;
    useReviewsStore().clear();
  }

  return { isAuthenticated, sessionChecked, login, restoreSession, logout, expireSession };
});
