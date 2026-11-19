<template>
  <div class="home">
    <AppNav link="review" @about="aboutOpen = true" />
    <div class="container">
      <form class="login-form" @submit.prevent="handleLogin">
        <h2 class="form-title">Admin Login</h2>
        <p class="form-subtitle">Authorised personnel only</p>

        <div class="form-group">
          <label for="email">
            Login
            <span class="required-mark" aria-hidden="true">*</span>
          </label>
          <input
            id="email"
            v-model="form.email"
            type="text"
            required
            placeholder="admin-artem-leo"
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">
            Password
            <span class="required-mark" aria-hidden="true">*</span>
          </label>
          <div class="password-field">
            <input
              id="password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="••••••••"
              autocomplete="current-password"
            />
            <button
              type="button"
              class="password-toggle"
              aria-label="Show password"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
                <line v-if="showPassword" x1="3" y1="3" x2="21" y2="21" />
              </svg>
            </button>
          </div>
        </div>

        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? "Authenticating ..." : "Sign In" }}
        </button>

        <transition name="slide-fade">
          <div v-if="error" class="error" role="alert">
            <svg
              class="error-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
            {{ error }}
          </div>
        </transition>

        <transition name="slide-fade">
          <div v-if="success" class="success" role="status">
            <svg
              class="success-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Access Granted! Redirecting ...
          </div>
        </transition>
      </form>
    </div>
  </div>
  <!-- Outside .home: its children are re-positioned to sit above the vignette. -->
  <AboutModal :open="aboutOpen" @close="aboutOpen = false" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { extractErrorMessage } from "@/utils/errors";
import AboutModal from "@/components/AboutModal.vue";
import AppNav from "@/components/AppNav.vue";

const router = useRouter();
const aboutOpen = ref(false);
const authStore = useAuthStore();

const DEMO_ACCOUNT = { email: "admin-artem-leo", password: "password-artem-leo" };

const form = ref({ ...DEMO_ACCOUNT });

const loading = ref(false);
const showPassword = ref(false);
const error = ref<string | null>(null);
const success = ref(false);

/**
 * How long the confirmation stays on screen before the redirect happens:
 * long enough to read two words, short enough not to feel like a slow login.
 */
const REDIRECT_DELAY_MS = 800;

/** Pending redirect after a successful sign-in. */
let redirectTimer: ReturnType<typeof setTimeout> | null = null;
/** Settles the pause before the redirect; `false` means the page was left. */
let finishPause: ((stay: boolean) => void) | null = null;
/** Prevents a late login response from redirecting a page the user already left. */
let pageLeft = false;

onBeforeUnmount(() => {
  pageLeft = true;
  if (redirectTimer !== null) clearTimeout(redirectTimer);
  // Settle the pending pause, so handleLogin finishes instead of hanging.
  finishPause?.(false);
});

async function handleLogin(): Promise<void> {
  loading.value = true;
  error.value = null;
  success.value = false;

  try {
    await authStore.login(form.value);
    if (pageLeft) return;

    success.value = true;
    form.value = { email: "", password: "" };

    // Give the user a moment to read "Access Granted!" before the dashboard
    // takes over the screen.
    // Leaving the page in the meantime cancels the redirect.
    const redirect = await new Promise<boolean>((resolve) => {
      finishPause = resolve;
      redirectTimer = setTimeout(() => resolve(true), REDIRECT_DELAY_MS);
    });
    finishPause = null;

    // The dashboard takes the login page's place in the history, so the
    // browser's Back button leaves the admin area instead of returning here.
    if (redirect) await router.replace("/admin");
  } catch (e: unknown) {
    // The backend owns the wording of the failure, including the 401 for
    // wrong credentials and the 429 for too many failed attempts.
    error.value = extractErrorMessage(e);
  } finally {
    loading.value = false;
  }
}

/** Clear the error once the user starts correcting the fields. */
watch(
  () => form.value,
  () => {
    error.value = null;
  },
  { deep: true }
);
</script>

<style scoped>
/* The photographic backdrop stays bright and sharp; only a soft vignette
   is laid over it so the eye lands on the login panel. */
.home {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  padding: 2rem;
  background-color: #0d111b;
  background-image: url("@/assets/images/home_view.webp");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
  color: #e2e8f0;
  font-family: "Inter", sans-serif;
}

/* A soft vignette pushes the eye towards the panel, while the photo
   keeps its brightness and sharpness around the edges. */

@media (max-width: 1920px) and (max-height: 1080px) and (max-resolution: 1dppx),
  (max-width: 1536px) and (max-height: 864px) and (max-resolution: 1.25dppx),
  (max-width: 1280px) and (max-height: 720px) and (max-resolution: 1.5dppx),
  (max-width: 960px) and (max-height: 540px) and (max-resolution: 2dppx) {
  .home {
    background-image: url("@/assets/images/home_view-1920.webp");
  }
}

@media (max-width: 1280px) and (max-height: 720px) and (max-resolution: 1dppx) {
  .home {
    background-image: url("@/assets/images/home_view-1280.webp");
  }
}

.home::before {
  content: "";
  position: fixed;
  inset: 0;
  background: radial-gradient(
    125% 95% at 50% 50%,
    rgba(13, 17, 27, 0) 0%,
    rgba(13, 17, 27, 0.22) 45%,
    rgba(8, 11, 17, 0.72) 100%
  );
  pointer-events: none;
  z-index: 0;
}

.home > * {
  position: relative;
  z-index: 1;
}

/* Auto margins centre the panel in the space left under the navigation. */
.container {
  max-width: 480px;
  width: 100%;
  margin: auto 0;
}

@media (max-width: 768px) {
  .container {
    max-width: 400px;
  }
}

@media (max-width: 480px) {
  .container {
    max-width: 100%;
  }
}

.login-form {
  position: relative;
  /* Fully opaque so the text stays readable over a bright photo. */
  background: linear-gradient(180deg, #1b2231 0%, #11161f 100%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 2.4rem;
  box-shadow:
    /* An amber rim light lifts the panel off the photograph. */
    0 0 0 1px rgba(245, 158, 11, 0.26),
    0 0 46px -12px rgba(245, 158, 11, 0.3),
    /* Deep ambient shadow for the 3D drop. */ 0 52px 100px -26px rgba(0, 0, 0, 0.88),
    0 24px 48px -20px rgba(0, 0, 0, 0.72),
    0 4px 12px -3px rgba(0, 0, 0, 0.55),
    /* Inner highlight along the top edge. */ inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.form-title {
  position: relative;
  font-family: "Rajdhani", sans-serif;
  font-size: 2rem;
  font-weight: 700;
  text-transform: uppercase;
  text-align: center;
  margin-bottom: 0.4rem;
  color: #f8fafc;
  letter-spacing: 2px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 0.9rem;
  text-shadow: 0 2px 12px rgba(245, 158, 11, 0.2);
}

/* Neutral grey seam under the title — same colour as the bottom border,
   no gradient or colour patch. */
.form-title::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 100%;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.08);
  pointer-events: none;
}

.form-subtitle {
  text-align: center;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #8492a6;
  margin-bottom: 2rem;
}

/* Required-field marker. The accent amber marks the field without the alarm
   of the red used for validation errors, so the two signals stay distinct. */
.required-mark {
  color: #f59e0b;
  font-weight: 700;
  margin-left: 0.2rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-family: "Rajdhani", sans-serif;
  font-weight: 600;
  color: #a0aec0;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

input {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  font-size: 0.95rem;
  font-family: "Inter", sans-serif;
  /* Recessed field: dark surface with an inner shadow. */
  background: rgba(8, 11, 17, 0.55);
  color: #f1f5f9;
  transition: all 0.2s ease;
  box-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.45),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
}

/* The eye button sits inside the right edge of the password field. */
.password-field {
  position: relative;
}

.password-field input {
  padding-right: 2.9rem;
}

.password-toggle {
  position: absolute;
  top: 50%;
  right: 0.5rem;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  outline: none;
  color: var(--ice-text);
  background: var(--ice-bg);
}

input::placeholder {
  color: #64748b;
}

input:focus {
  outline: none;
  border-color: rgba(245, 158, 11, 0.7); /* Tactical orange accent */
  box-shadow:
    inset 0 1px 3px rgba(0, 0, 0, 0.4),
    0 0 0 3px rgba(245, 158, 11, 0.2);
  background: rgba(8, 11, 17, 0.7);
}

.submit-btn {
  width: 100%;
  padding: 0.9rem;
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  color: #1c1305;
  border: none;
  border-radius: 6px;
  font-family: "Rajdhani", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.5rem;
  box-shadow:
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, #fcd34d 0%, #f59e0b 58%, #e08e05 100%);
  transform: translateY(-1px);
  box-shadow:
    0 8px 18px -4px rgba(245, 158, 11, 0.35),
    0 2px 6px -1px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  background: rgba(245, 158, 11, 0.45);
  color: rgba(28, 19, 5, 0.7);
  cursor: not-allowed;
  box-shadow: none;
}

.error {
  margin-top: 1rem;
  padding: 0.75rem;
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.16), rgba(239, 68, 68, 0.07));
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #fecaca;
  border-radius: 8px;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow:
    0 6px 16px -8px rgba(239, 68, 68, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.error-icon {
  flex-shrink: 0;
}

.success {
  margin-top: 1rem;
  padding: 0.75rem;
  background: linear-gradient(180deg, rgba(16, 185, 129, 0.16), rgba(16, 185, 129, 0.06));
  border: 1px solid rgba(16, 185, 129, 0.32);
  color: #a7f3d0;
  border-radius: 8px;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow:
    0 6px 16px -8px rgba(16, 185, 129, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.success-icon {
  flex-shrink: 0;
}

/* Slide-fade transition for messages */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.5s ease;
  max-height: 100px;
  opacity: 1;
  margin-top: 1rem;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  max-height: 0;
  opacity: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}

/* Responsive design */
@media (max-width: 640px) {
  .home {
    padding: 10px;
  }

  .login-form {
    padding: 1.5rem;
  }

  .form-title {
    font-size: 1.6rem;
    letter-spacing: 1.5px;
  }

  label {
    font-size: 0.8rem;
  }

  input {
    font-size: 0.9rem;
    padding: 0.7rem 0.9rem;
  }

  .submit-btn {
    font-size: 1rem;
    padding: 0.8rem;
  }
}
</style>
