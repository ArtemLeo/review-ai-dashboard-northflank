// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import PaginationBar from "@/components/admin/PaginationBar.vue";

const props = { currentPage: 2, totalPages: 3, rangeStart: 11, rangeEnd: 20, total: 25 };

describe("PaginationBar", () => {
  it("shows the range and the current page", () => {
    const wrapper = mount(PaginationBar, { props });

    expect(wrapper.text()).toContain("11–20 of 25");
    expect(wrapper.get(".page-indicator").text()).toBe("Page 2 / 3");
  });

  it("asks for the previous and the next page", async () => {
    const wrapper = mount(PaginationBar, { props });

    await wrapper.get("[aria-label='Previous page']").trigger("click");
    await wrapper.get("[aria-label='Next page']").trigger("click");

    expect(wrapper.emitted("go-to-page")).toEqual([[1], [3]]);
  });

  it("disables the arrows at the edges", () => {
    const wrapper = mount(PaginationBar, { props: { ...props, currentPage: 1, totalPages: 1 } });

    expect(wrapper.find(".pagination-panel").exists()).toBe(false);

    const first = mount(PaginationBar, { props: { ...props, currentPage: 1 } });
    expect(first.get("[aria-label='Previous page']").attributes("disabled")).toBeDefined();
    expect(first.get("[aria-label='Next page']").attributes("disabled")).toBeUndefined();

    const last = mount(PaginationBar, { props: { ...props, currentPage: 3 } });
    expect(last.get("[aria-label='Previous page']").attributes("disabled")).toBeUndefined();
    expect(last.get("[aria-label='Next page']").attributes("disabled")).toBeDefined();
  });
});
