import { RefObject, useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR = [
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled]):not([type='hidden'])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
].join(",");

// `offsetParent !== null` catches `display:none` on the element or any
// ancestor; it won't catch `visibility:hidden`. Dialog descendants in this
// codebase use `display:none` (or mount/unmount) for hidden states, so the
// check is sufficient here.
function getFocusable(container: HTMLElement): HTMLElement[] {
    return Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    ).filter(
        (el) =>
            !el.hasAttribute("disabled") &&
            el.getAttribute("aria-hidden") !== "true" &&
            el.offsetParent !== null,
    );
}

export interface UseDialogKeyboardOptions {
    isOpen: boolean;
    onClose: () => void;
    containerRef: RefObject<HTMLElement | null>;
}

/**
 * Makes a dialog/sheet WCAG-compliant: Escape dismisses it, Tab/Shift+Tab
 * cycle focus inside the container, and focus is restored to the previously
 * active element when it closes. The container element itself must accept
 * programmatic focus (set `tabIndex={-1}`) so it can serve as the fallback
 * target when no focusable descendants exist.
 */
export function useDialogKeyboard({
    isOpen,
    onClose,
    containerRef,
}: UseDialogKeyboardOptions): void {
    const onCloseRef = useRef(onClose);
    useEffect(() => {
        onCloseRef.current = onClose;
    }, [onClose]);

    useEffect(() => {
        if (!isOpen) return;
        const container = containerRef.current;
        if (!container) return;

        const previousFocus =
            document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;

        const raf = requestAnimationFrame(() => {
            if (!container.contains(document.activeElement)) {
                const focusable = getFocusable(container);
                (focusable[0] ?? container).focus();
            }
        });

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                // Use stopImmediatePropagation so a stacked dialog (e.g.
                // LoginModal over the calendar sheet) only closes the top one.
                e.stopImmediatePropagation();
                onCloseRef.current();
                return;
            }
            if (e.key !== "Tab") return;
            const focusable = getFocusable(container);
            if (focusable.length === 0) {
                e.preventDefault();
                container.focus();
                return;
            }
            const active = document.activeElement as HTMLElement | null;
            const currentIdx = active ? focusable.indexOf(active) : -1;
            e.preventDefault();
            const lastIdx = focusable.length - 1;
            let nextIdx: number;
            if (e.shiftKey) {
                nextIdx = currentIdx <= 0 ? lastIdx : currentIdx - 1;
            } else {
                nextIdx =
                    currentIdx === -1 || currentIdx === lastIdx
                        ? 0
                        : currentIdx + 1;
            }
            focusable[nextIdx].focus();
        };

        document.addEventListener("keydown", handleKeyDown);
        return () => {
            cancelAnimationFrame(raf);
            document.removeEventListener("keydown", handleKeyDown);
            previousFocus?.focus?.();
        };
    }, [isOpen, containerRef]);
}
