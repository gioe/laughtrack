/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import NavigationMenu from "@/ui/components/navbar/menu";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

// Routes the May 2026 cross-page consistency audit flagged as missing the
// top-nav category dropdowns. The audit used a depth-limited Playwright
// snapshot which collapsed the Popover subtree on busy pages; the dropdowns
// actually render on every route. This test pins that behavior so the menu
// stays consistent if anyone later wires the dropdown list to pathname.
const AFFECTED_ROUTES = [
    "/comedian/Steve-O",
    "/podcast/the-joe-rogan-experience",
    "/club/search",
    "/comedian/search",
    "/show/search",
    "/podcast/search",
];

const CATEGORY_LABELS = ["Shows", "Comedians", "Clubs", "Podcasts"] as const;

describe("Top-nav category dropdowns", () => {
    afterEach(() => {
        cleanup();
    });

    it.each(AFFECTED_ROUTES)(
        "renders all four category dropdown buttons on %s",
        (pathname) => {
            const { getByRole } = render(
                <StyleContextProvider initialContext={StyleContextKey.Search}>
                    <NavigationMenu pathname={pathname} />
                </StyleContextProvider>,
            );

            for (const label of CATEGORY_LABELS) {
                expect(getByRole("button", { name: label })).not.toBeNull();
            }
        },
    );

    it("does not leave an empty wrapper around the category buttons", () => {
        const { getByRole, getAllByRole } = render(
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <NavigationMenu pathname="/comedian/search" />
            </StyleContextProvider>,
        );

        const buttons = getAllByRole("button").filter((b) =>
            CATEGORY_LABELS.includes(
                b.textContent?.trim() as (typeof CATEGORY_LABELS)[number],
            ),
        );
        expect(buttons).toHaveLength(CATEGORY_LABELS.length);

        // The buttons must share a single parent (the PopoverGroup wrapper).
        const parents = new Set(buttons.map((b) => b.parentElement?.parentElement));
        expect(parents.size).toBe(1);
        const wrapper = buttons[0].parentElement?.parentElement;
        expect(wrapper?.children.length).toBe(CATEGORY_LABELS.length);

        // Static items remain available outside the wrapper.
        expect(getByRole("link", { name: "Near Me" })).not.toBeNull();
        expect(getByRole("link", { name: "Search" })).not.toBeNull();
    });
});
