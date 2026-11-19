// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ReviewTable from "@/components/admin/ReviewTable.vue";
import { makeReview } from "@/test/fixtures";
import { AnalysisStatus, Priority } from "@/types";

describe("ReviewTable", () => {
  it("shows short headers and one row per review, numbered by page", () => {
    const wrapper = mount(ReviewTable, {
      props: {
        reviews: [makeReview({ id: "a" }), makeReview({ id: "b" })],
        currentPage: 2,
        pageSize: 10,
      },
    });

    const headers = wrapper.findAll("th").map((th) => th.text());
    expect(headers).toEqual(expect.arrayContaining(["Priority", "Rating", "Status"]));
    const numbers = wrapper.findAll("td.num").map((td) => td.text());
    expect(numbers).toEqual(["11", "12"]);
  });

  it("renders the badges and the stars of a review", () => {
    const wrapper = mount(ReviewTable, {
      props: {
        reviews: [
          makeReview({
            priority: Priority.High,
            rating: 2,
            analysis_status: AnalysisStatus.Completed,
          }),
        ],
        currentPage: 1,
        pageSize: 10,
      },
    });

    expect(wrapper.get(".priority.high").text()).toBe("High");
    expect(wrapper.get(".status.completed").text()).toBe("Completed");
    expect(wrapper.get(".star-rating").text()).toBe("★★☆☆☆");
    expect(wrapper.get(".star-rating").attributes("aria-label")).toBe("2 of 5 stars");
  });

  it("opens a review from the keyboard", async () => {
    const review = makeReview({ id: "keyboard" });
    const wrapper = mount(ReviewTable, {
      props: { reviews: [review], currentPage: 1, pageSize: 10 },
    });
    const row = wrapper.get("tr.review-row");

    expect(row.attributes("tabindex")).toBe("0");
    await row.trigger("keydown", { key: "Enter" });
    await row.trigger("keydown", { key: " " });

    expect(wrapper.emitted("select")).toEqual([[review], [review]]);
  });

  it("reports the clicked review", async () => {
    const review = makeReview({ id: "clicked" });
    const wrapper = mount(ReviewTable, {
      props: { reviews: [review], currentPage: 1, pageSize: 10 },
    });

    await wrapper.get("tr.review-row").trigger("click");

    expect(wrapper.emitted("select")).toEqual([[review]]);
  });
});
