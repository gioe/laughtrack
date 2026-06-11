/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { SearchChipRow } from "./index";

describe("SearchChipRow", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders children inside a group named by ariaLabel", () => {
        const { container } = render(
            <SearchChipRow ariaLabel="Show filters">
                <button type="button">Chip</button>
            </SearchChipRow>,
        );
        const group = container.querySelector('[role="group"]');
        expect(group?.getAttribute("aria-label")).toBe("Show filters");
        expect(group?.querySelector("button")?.textContent).toBe("Chip");
    });
});
