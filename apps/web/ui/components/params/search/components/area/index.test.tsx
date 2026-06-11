/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { ComponentVariant, StyleContextKey } from "@/objects/enum";
import ShowLocationComponent from "./index";

vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: vi.fn(),
        setTypedParam: vi.fn(),
    }),
}));

vi.mock("@/app/actions/resolveLocationAction", () => ({
    resolveLocationAction: vi.fn(async () => ({ ok: true })),
}));

function renderStandalone(
    value: { distance: string | null; zipCode: string | null } = {
        distance: "25",
        zipCode: "90210",
    },
) {
    return render(
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <ShowLocationComponent
                variant={ComponentVariant.Standalone}
                value={value}
            />
        </StyleContextProvider>,
    );
}

describe("ShowLocationComponent Standalone chip row", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders the distance pill as a group labelled 'Search radius'", () => {
        const { container } = renderStandalone();
        const pill = container.querySelector('[role="group"]');
        expect(pill?.getAttribute("aria-label")).toBe("Search radius");
    });

    it("shows the selected distance with the mi unit in the pill", () => {
        const { getByRole } = renderStandalone();
        const trigger = getByRole("combobox");
        expect(trigger.textContent).toContain("25 mi");
    });

    it("strips the dropdown trigger chrome via the triggerClassName passthrough", () => {
        const { getByRole } = renderStandalone();
        const trigger = getByRole("combobox");
        expect(trigger.className).toContain("bg-transparent");
        expect(trigger.className).toContain("border-0");
    });

    it("renders the zip pill input named by its placeholder", () => {
        const { container } = renderStandalone();
        const input = container.querySelector(
            'input[aria-label="City or zip code"]',
        ) as HTMLInputElement | null;
        expect(input).not.toBeNull();
        expect(input?.value).toBe("90210");
    });

    it("renders the geolocate button", () => {
        const { container } = renderStandalone();
        const geo = container.querySelector(
            'button[aria-label="Use my location"]',
        );
        expect(geo).not.toBeNull();
    });
});
