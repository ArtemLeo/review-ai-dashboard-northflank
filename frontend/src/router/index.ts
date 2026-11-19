import { createRouter, createWebHistory } from "vue-router";
import type { RouteRecordRaw } from "vue-router";
import { SESSION_EXPIRED_EVENT } from "@/services/api";
import { useAuthStore } from "@/stores/auth";

/** Application route definitions with lazy-loaded view components. */
const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/HomeView.vue"),
  },
  {
    path: "/admin/login",
    name: "admin-login",
    component: () => import("@/views/AdminLoginView.vue"),
  },
  {
    path: "/admin",
    name: "admin-dashboard",
    component: () => import("@/views/AdminDashboardView.vue"),
    meta: { requiresAuth: true },
  },
  // nginx answers every unknown path with the app, so the router must not
  // leave such a page blank: it leads to the home page instead.
  {
    path: "/:pathMatch(.*)*",
    redirect: { name: "home" },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

/**
 * Global navigation guard.
 * Redirects unauthenticated users away from protected routes,
 * and redirects already-authenticated users away from the login page.
 * The session is confirmed with the server once per page load, the first
 * time one of these two pages is opened.
 */
router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  const needsSession = to.meta.requiresAuth === true || to.name === "admin-login";

  // The session lives in an httpOnly cookie, so only the server can tell.  The
  // public form never needs it, so its visitors send no request that would
  // only come back 401.
  if (needsSession && !authStore.sessionChecked) {
    await authStore.restoreSession();
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: "admin-login" };
  }
  if (to.name === "admin-login" && authStore.isAuthenticated) {
    return { name: "admin-dashboard" };
  }
  return true;
});

/** An expired session sends the admin back to the login page, in place. */
window.addEventListener(SESSION_EXPIRED_EVENT, () => {
  useAuthStore().expireSession();
  if (router.currentRoute.value.name !== "admin-login") {
    void router.replace({ name: "admin-login" });
  }
});

export default router;
