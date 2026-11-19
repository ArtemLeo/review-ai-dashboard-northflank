// @vitest-environment jsdom
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import BaseModal from "@/components/admin/BaseModal.vue";

describe("BaseModal", () => {
  it("is labelled by its title", () => {
    const wrapper = mount(BaseModal, { props: { open: true, title: "Details" } });

    const dialog = wrapper.get("[role='dialog']");
    const titleId = dialog.attributes("aria-labelledby");
    expect(wrapper.get(`#${titleId}`).text()).toBe("Details");
  });

  it("closes on Escape, on the overlay and on the close button", async () => {
    const wrapper = mount(BaseModal, { props: { open: true, title: "Details" } });

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await wrapper.get(".modal-overlay").trigger("mousedown");
    await wrapper.get(".modal-overlay").trigger("click");
    await wrapper.get(".modal-close").trigger("click");

    expect(wrapper.emitted("close")).toHaveLength(3);
  });

  it("stays open when a text selection inside it ends over the overlay", async () => {
    const wrapper = mount(BaseModal, { props: { open: true, title: "Details" } });

    await wrapper.get("[role='dialog']").trigger("mousedown");
    await wrapper.get(".modal-overlay").trigger("click");

    expect(wrapper.emitted("close")).toBeUndefined();
  });

  it("ignores Escape while closed", () => {
    const wrapper = mount(BaseModal, { props: { open: false, title: "Details" } });

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    expect(wrapper.emitted("close")).toBeUndefined();
  });

  it("moves the focus in on open and gives it back on close", async () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const wrapper = mount(BaseModal, {
      props: { open: false, title: "Details" },
      attachTo: document.body,
    });

    await wrapper.setProps({ open: true });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get("[role='dialog']").element);

    await wrapper.setProps({ open: false });
    expect(document.activeElement).toBe(opener);

    wrapper.unmount();
    opener.remove();
  });

  it("keeps Tab and Shift+Tab inside the dialog", async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true, title: "Details" },
      slots: { default: "<button>One</button><button>Two</button>" },
      attachTo: document.body,
    });
    await nextTick();
    const dialog = wrapper.get("[role='dialog']");
    const buttons = dialog.findAll("button").map((button) => button.element as HTMLElement);
    const first = buttons[0];
    const last = buttons[buttons.length - 1];

    last.focus();
    await dialog.trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(first);

    await dialog.trigger("keydown", { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);

    wrapper.unmount();
  });

  it("closes only the top-most dialog on Escape", async () => {
    const lower = mount(BaseModal, { props: { open: true, title: "Lower" } });
    const upper = mount(BaseModal, { props: { open: true, title: "Upper" } });
    await nextTick();

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    expect(upper.emitted("close")).toHaveLength(1);
    expect(lower.emitted("close")).toBeUndefined();
    upper.unmount();
    lower.unmount();
  });
});
