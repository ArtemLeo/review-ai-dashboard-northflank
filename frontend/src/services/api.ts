import axios from "axios";

/**
 * Shared Axios instance — every request goes to the same-origin /api path,
 * which nginx proxies to the API in the image and the Vite dev server proxies
 * in development.  The session lives in an httpOnly cookie, so every request
 * must carry credentials; page scripts never see the token itself.
 */
const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
  // Double-submit CSRF protection: axios copies the readable XSRF-TOKEN
  // cookie into the X-XSRF-TOKEN header of every same-origin request.
  xsrfCookieName: "XSRF-TOKEN",
  xsrfHeaderName: "X-XSRF-TOKEN",
});

/** Endpoints whose 401 is an expected answer and must not redirect the page. */
const SESSION_PROBE_PATHS: readonly string[] = ["/auth/login", "/auth/me"];

/** Window event fired when the server rejects the session (HTTP 401). */
export const SESSION_EXPIRED_EVENT = "auth:session-expired";

/**
 * Global 401 handler.  The API layer does not know the router (importing it
 * here would create a cycle), so it only announces the expired session; the
 * router listens, clears the auth state and moves to the login page without
 * a full page reload.  Session probes handle their own 401.
 */
api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const path = error.config?.url ?? "";
      const isSessionProbe = SESSION_PROBE_PATHS.some((probe) => path.includes(probe));
      if (!isSessionProbe) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  }
);

export default api;
