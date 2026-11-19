// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AdminToolbar from "@/components/admin/AdminToolbar.vue";
import { makePagination } from "@/test/fixtures";

function mountToolbar(exporting = false) {
  return mount(AdminToolbar, {
    props: { filters: {}, exporting, pagination: makePagination() },
  });
}

describe("AdminToolbar", () => {
  it("reports the field and the raw value of a changed filter", async () => {
    const wrapper = mountToolbar();

    await wrapper.get('select[data-filter="status"]').setValue("Pending");
    await wrapper.get('select[data-filter="rating"]').setValue("4");
    await wrapper.get('select[data-filter="priority"]').setValue("");

    expect(wrapper.emitted("filter-change")).toEqual([
      ["status", "Pending"],
      ["rating", "4"],
      ["priority", ""],
    ]);
  });

  it("offers an empty 'All ...' option in every filter", () => {
    const wrapper = mountToolbar();

    expect(wrapper.findAll('select option[value=""]')).toHaveLength(3);
  });

  it("emits the toolbar actions", async () => {
    const wrapper = mountToolbar();

    await wrapper.get(".statistics-btn").trigger("click");
    await wrapper.get(".refresh-btn").trigger("click");
    await wrapper.get('button[data-action="export"]').trigger("click");

    expect(wrapper.emitted("show-statistics")).toHaveLength(1);
    expect(wrapper.emitted("refresh")).toHaveLength(1);
    expect(wrapper.emitted("export")).toHaveLength(1);
  });

  it("disables the export button while a download is running", () => {
    const wrapper = mountToolbar(true);

    expect(wrapper.get('button[data-action="export"]').attributes()).toHaveProperty("disabled");
  });
});
