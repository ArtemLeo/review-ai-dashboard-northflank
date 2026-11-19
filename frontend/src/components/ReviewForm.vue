<template>
  <form class="review-form" @submit.prevent="submit">
    <header class="form-heading">
      <h1>Share Your Feedback</h1>
      <p>Your feedback makes our product better</p>
    </header>

    <div class="form-group">
      <label for="authorName">Name <span aria-hidden="true">*</span></label>
      <input
        id="authorName"
        v-model.trim="form.author_name"
        autocomplete="name"
        maxlength="150"
        required
        placeholder="John Smith"
      />
    </div>

    <div class="form-group">
      <label for="email">Email <span aria-hidden="true">*</span></label>
      <input
        id="email"
        v-model.trim="form.email"
        type="email"
        autocomplete="email"
        maxlength="254"
        required
        placeholder="john@example.com"
      />
    </div>

    <div class="form-group">
      <label for="reviewText">Review <span aria-hidden="true">*</span></label>
      <textarea
        id="reviewText"
        v-model.trim="form.text"
        maxlength="10000"
        required
        rows="5"
        placeholder="Share your experience ..."
      ></textarea>
    </div>

    <button class="submit-btn" type="submit" :disabled="loading">
      {{ loading ? "Submitting ..." : "Submit Review" }}
    </button>

    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <p v-if="success" class="message success" role="status">Review submitted successfully!</p>
  </form>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { reviewService } from "@/services/reviewService";
import type { CreateReviewRequest } from "@/types";
import { extractErrorMessage } from "@/utils/errors";

const form = reactive<CreateReviewRequest>({ author_name: "", email: "", text: "" });
const loading = ref(false);
const success = ref(false);
const error = ref<string | null>(null);

async function submit(): Promise<void> {
  loading.value = true;
  success.value = false;
  error.value = null;
  try {
    await reviewService.createReview({ ...form });
    success.value = true;
    form.author_name = "";
    form.email = "";
    form.text = "";
  } catch (cause: unknown) {
    error.value = extractErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.review-form {
  width: 100%;
  padding: 2.4rem;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: linear-gradient(180deg, #1b2231 0%, #11161f 100%);
  box-shadow:
    0 0 0 1px rgba(245, 158, 11, 0.26),
    0 0 46px -12px rgba(245, 158, 11, 0.3),
    0 42px 85px -24px rgba(0, 0, 0, 0.88),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.form-heading {
  margin-bottom: 2rem;
  text-align: center;
}

.form-heading h1 {
  margin: 0;
  padding: 0 0 1.3rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  color: #f8fafc;
  font-family: "Rajdhani", sans-serif;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1.1;
  text-transform: uppercase;
}

.form-heading p {
  margin: 0;
  padding-top: 0.8rem;
  color: #8492a6;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.form-group {
  margin-bottom: 1.25rem;
}

label {
  display: block;
  margin-bottom: 0.65rem;
  color: #a0aec0;
  font-family: "Rajdhani", sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

label span {
  padding-left: 0.2rem;
  color: #f59e0b;
}

input,
textarea {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(8, 11, 17, 0.62);
  box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.4);
  color: #f1f5f9;
  font: inherit;
  font-size: 0.95rem;
  padding: 0.8rem 1rem;
}

input::placeholder,
textarea::placeholder {
  color: #64748b;
}

input:focus,
textarea:focus {
  border-color: rgba(245, 158, 11, 0.7);
  outline: 3px solid rgba(245, 158, 11, 0.18);
}

textarea {
  min-height: 100px;
  resize: vertical;
}

.submit-btn {
  width: 100%;
  min-height: 3.2rem;
  margin-top: 0.35rem;
  border: 0;
  border-radius: 6px;
  background: linear-gradient(180deg, #fbbf24 0%, #f59e0b 58%, #dd8b04 100%);
  box-shadow:
    0 5px 14px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
  color: #1c1305;
  cursor: pointer;
  font-family: "Rajdhani", sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.submit-btn:hover:not(:disabled) {
  filter: brightness(1.08);
}

.submit-btn:disabled {
  cursor: wait;
  opacity: 0.7;
}

.message {
  margin: 1rem 0 0;
  padding: 0.85rem 1rem;
  border-radius: 8px;
  text-align: center;
}

.error {
  border: 1px solid rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.12);
  color: #fecaca;
}

.success {
  border: 1px solid rgba(16, 185, 129, 0.32);
  background: rgba(16, 185, 129, 0.12);
  color: #a7f3d0;
}
</style>
