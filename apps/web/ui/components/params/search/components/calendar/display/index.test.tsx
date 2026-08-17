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
import { getChipPresets } from "./presets";

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
        vi.useRealTimers();
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

    // NOTE: TASK-2810 removed a "rounded pill when pill is set" test that
    // asserted a `pill` prop CalendarDisplay does not have — the trigger is
    // unconditionally pill-shaped today. If TASK-2794 introduces a pill/plain
    // variant API, reintroduce variant tests alongside that prop.

    it("renders the pill trigger as the single Any date control by default", () => {
        const { container } = renderDisplay();
        const trigger = container.querySelector("button");
        expect(trigger?.className).toContain("rounded-full");
        expect(trigger?.textContent).toContain("Any date");
    });

    it("offers clearing, Tonight, and a Friday-through-Sunday weekend inside the control", () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date(2026, 7, 12, 12)); // Wednesday

        const presets = getChipPresets();
        expect(presets.slice(0, 3).map(({ label }) => label)).toEqual([
            "Any date",
            "Tonight",
            "Tomorrow",
        ]);
        expect(
            presets.find(({ label }) => label === "Any date")?.range,
        ).toBeUndefined();

        const weekend = presets.find(
            ({ label }) => label === "This Weekend",
        )?.range;
        expect(weekend?.from).toEqual(new Date(2026, 7, 14));
        expect(weekend?.to).toEqual(new Date(2026, 7, 16));
    });
});
