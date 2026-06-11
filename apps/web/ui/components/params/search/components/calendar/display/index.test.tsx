/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { DateRange } from "@/objects/interface";
import { CalendarDisplay } from "./index";

// useDialogKeyboard is the only @/hooks import in CalendarDisplay; mocking the
// barrel keeps the rest of the hook chain (next/navigation) out of happy-dom.
vi.mock("@/hooks", () => ({
    useDialogKeyboard: vi.fn(),
}));

const emptyRange: DateRange = { from: undefined, to: undefined };

function renderDisplay(
    props: Partial<React.ComponentProps<typeof CalendarDisplay>> = {},
) {
    return render(
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <CalendarDisplay
                selectedRange={emptyRange}
                onSelect={vi.fn()}
                {...props}
            />
        </StyleContextProvider>,
    );
}

describe("CalendarDisplay trigger", () => {
    afterEach(() => {
        cleanup();
    });

    it("falls back to a 'Select dates' aria-label when no ariaLabelledBy is passed", () => {
        const { container } = renderDisplay();
        const trigger = container.querySelector("button");
        expect(trigger?.getAttribute("aria-label")).toBe("Select dates");
        expect(trigger?.hasAttribute("aria-labelledby")).toBe(false);
    });

    it("uses aria-labelledby instead of the fallback when ariaLabelledBy is passed", () => {
        const { container } = renderDisplay({ ariaLabelledBy: "when-label" });
        const trigger = container.querySelector("button");
        expect(trigger?.getAttribute("aria-labelledby")).toBe("when-label");
        expect(trigger?.hasAttribute("aria-label")).toBe(false);
    });

    it("renders the trigger as a rounded pill when pill is set", () => {
        const { container } = renderDisplay({ pill: true });
        const trigger = container.querySelector("button");
        expect(trigger?.className).toContain("rounded-full");
    });

    it("keeps the plain trigger and shows the placeholder by default", () => {
        const { container } = renderDisplay();
        const trigger = container.querySelector("button");
        expect(trigger?.className).not.toContain("rounded-full");
        expect(trigger?.textContent).toContain("When");
    });
});
