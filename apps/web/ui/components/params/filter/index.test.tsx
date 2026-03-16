/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { FilterModalButton } from "./index";

vi.mock("@/hooks", () => ({
    useFilterModal: () => ({
        isOpen: false,
        onOpen: vi.fn(),
        onClose: vi.fn(),
    }),
}));

describe("FilterModalButton", () => {
    describe("badge text", () => {
        it.each([1, 3, 5, 9])(
            "shows the raw count %i for values 1-9",
            (count) => {
                const { container } = render(
                    <FilterModalButton filterCount={count} />,
                );
                const badge = container.querySelector(".rounded-full");
                expect(badge?.textContent).toBe(String(count));
            },
        );

        it("shows '9+' when filterCount is exactly 10", () => {
            const { container } = render(
                <FilterModalButton filterCount={10} />,
            );
            const badge = container.querySelector(".rounded-full");
            expect(badge?.textContent).toBe("9+");
        });

        it("shows '9+' when filterCount is greater than 10", () => {
            const { container } = render(
                <FilterModalButton filterCount={25} />,
            );
            const badge = container.querySelector(".rounded-full");
            expect(badge?.textContent).toBe("9+");
        });

        it("does not render a badge when filterCount is 0", () => {
            const { container } = render(<FilterModalButton filterCount={0} />);
            expect(container.querySelector(".rounded-full")).toBeNull();
        });

        it("does not render a badge when filterCount is omitted", () => {
            const { container } = render(<FilterModalButton />);
            expect(container.querySelector(".rounded-full")).toBeNull();
        });
    });
});
