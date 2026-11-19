<template>
  <main class="home">
    <AppNav link="admin" @about="aboutOpen = true" />
    <div class="form-wrap">
      <ReviewForm />
    </div>
  </main>
  <AboutModal :open="aboutOpen" @close="aboutOpen = false" />
</template>

<script setup lang="ts">
import { ref } from "vue";
import AppNav from "@/components/AppNav.vue";
import AboutModal from "@/components/AboutModal.vue";
import ReviewForm from "@/components/ReviewForm.vue";

const aboutOpen = ref(false);
</script>

<style scoped>
.home {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  min-height: 100vh;
  padding: 2rem;
  background-color: #0d111b;
  background-image: url("@/assets/images/home_view.webp");
  background-position: center;
  background-size: cover;
  color: #e2e8f0;
  font-family: "Inter", sans-serif;
}

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
  position: fixed;
  z-index: 0;
  background: radial-gradient(
    125% 95% at 50% 50%,
    rgba(13, 17, 27, 0.16) 0%,
    rgba(13, 17, 27, 0.38) 50%,
    rgba(8, 11, 17, 0.76) 100%
  );
  content: "";
  inset: 0;
  pointer-events: none;
}

.form-wrap {
  z-index: 1;
  width: min(100%, 480px);
  margin: auto 0;
}

@media (max-width: 768px) {
  .form-wrap {
    max-width: 400px;
  }
}

@media (max-width: 480px) {
  .home {
    padding: 1rem;
  }
}
</style>
