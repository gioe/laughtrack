/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { RefObject } from "react";
import { useDialogKeyboard } from "./useDialogKeyboard";

function mountContainer(html: string): HTMLDivElement {
    const container = document.createElement("div");
    container.tabIndex = -1;
    container.innerHTML = html;
    document.body.appendChild(container);
    return container;
}

function renderDialogHook(
    container: HTMLElement,
    onClose: () => void,
    initialOpen: boolean = true,
) {
    const ref: RefObject<HTMLElement | null> = { current: container };
    return renderHook(
        ({ open }: { open: boolean }) =>
            useDialogKeyboard({
                isOpen: open,
                onClose,
                containerRef: ref,
            }),
        { initialProps: { open: initialOpen } },
    );
}

beforeEach(() => {
    document.body.innerHTML = "";
    // Make requestAnimationFrame synchronous so the auto-focus effect fires
    // before test assertions without needing to await a frame.
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
        cb(0);
        return 0;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("useDialogKeyboard", () => {
    describe("Escape handling", () => {
        it("calls onClose when Escape is pressed while open", () => {
            const container = mountContainer(`<button>One</button>`);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, true);

            document.dispatchEvent(
                new KeyboardEvent("keydown", { key: "Escape" }),
            );

            expect(onClose).toHaveBeenCalledTimes(1);
        });

        it("does not invoke onClose when isOpen is false", () => {
            const container = mountContainer(`<button>One</button>`);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, false);

            document.dispatchEvent(
                new KeyboardEvent("keydown", { key: "Escape" }),
            );

            expect(onClose).not.toHaveBeenCalled();
        });
    });

    describe("Tab focus trap", () => {
        it("wraps Tab from the last focusable back to the first", () => {
            const container = mountContainer(`
                <button id="b1">One</button>
                <button id="b2">Two</button>
                <button id="b3">Three</button>
            `);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, true);

            const last = container.querySelector<HTMLButtonElement>("#b3")!;
            last.focus();
            expect(document.activeElement).toBe(last);

            document.dispatchEvent(
                new KeyboardEvent("keydown", { key: "Tab" }),
            );

            expect((document.activeElement as HTMLElement).id).toBe("b1");
        });

        it("wraps Shift+Tab from the first focusable back to the last", () => {
            const container = mountContainer(`
                <button id="b1">One</button>
                <button id="b2">Two</button>
                <button id="b3">Three</button>
            `);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, true);

            const first = container.querySelector<HTMLButtonElement>("#b1")!;
            first.focus();
            expect(document.activeElement).toBe(first);

            document.dispatchEvent(
                new KeyboardEvent("keydown", {
                    key: "Tab",
                    shiftKey: true,
                }),
            );

            expect((document.activeElement as HTMLElement).id).toBe("b3");
        });
    });

    describe("focus restoration", () => {
        it("restores focus to the previously-active element when isOpen flips false", () => {
            const trigger = document.createElement("button");
            trigger.id = "trigger";
            document.body.appendChild(trigger);
            trigger.focus();
            expect(document.activeElement).toBe(trigger);

            const container = mountContainer(
                `<button id="inner">Inner</button>`,
            );
            const onClose = vi.fn();
            const { rerender } = renderDialogHook(container, onClose, true);

            // Simulate focus moving into the dialog (e.g. the auto-focus effect
            // or a user tab).
            container.querySelector<HTMLButtonElement>("#inner")!.focus();
            expect(document.activeElement).not.toBe(trigger);

            rerender({ open: false });

            expect(document.activeElement).toBe(trigger);
        });
    });

    describe("auto-focus on open", () => {
        it("moves focus to the first focusable descendant when nothing inside was focused on mount", () => {
            const container = mountContainer(`
                <button id="b1">One</button>
                <button id="b2">Two</button>
            `);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, true);

            expect((document.activeElement as HTMLElement).id).toBe("b1");
        });

        it("focuses the container itself when no focusable descendants exist", () => {
            const container = mountContainer(``);
            const onClose = vi.fn();
            renderDialogHook(container, onClose, true);

            expect(document.activeElement).toBe(container);
        });
    });
});
