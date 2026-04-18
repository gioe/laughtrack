/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import FilterModal from "./index";
import { SearchVariant } from "@/objects/enum/searchVariant";

vi.mock("@/hooks", () => ({
    useFilterModal: () => ({ isOpen: true, onClose: vi.fn() }),
}));
vi.mock("@/hooks/useFilters", () => ({
    useFilters: () => ({
        handleOpen: vi.fn(),
        handleFilterChange: vi.fn(),
        handleClose: vi.fn(),
        selections: [],
    }),
}));
// Replace the rich children with sentinels so we don't depend on their full
// dependency graph (zip resolution, calendar popover, etc.) in unit tests.
vi.mock("./comedianAdvanced", () => ({
    default: () => <div data-testid="comedian-advanced-filters" />,
}));
vi.mock("../../params/filter/chips", () => ({
    FilterChip: ({ option }: { option: { name: string } }) => (
        <div data-testid={`chip-${option.name}`}>{option.name}</div>
    ),
}));

describe("FilterModal", () => {
    const aliasFilter = { id: 1, slug: "alias", name: "Comedian Alias" };

    it("renders ComedianAdvancedFilters when variant is AllComedians", () => {
        const { container } = render(
            <FilterModal
                filters={[aliasFilter]}
                total={42}
                variant={SearchVariant.AllComedians}
            />,
        );
        expect(
            container.querySelector(
                '[data-testid="comedian-advanced-filters"]',
            ),
        ).not.toBeNull();
    });

    it("preserves the existing tag-chip section alongside the advanced filters", () => {
        const { container } = render(
            <FilterModal
                filters={[aliasFilter]}
                total={42}
                variant={SearchVariant.AllComedians}
            />,
        );
        expect(
            container.querySelector('[data-testid="chip-Comedian Alias"]'),
        ).not.toBeNull();
    });

    it("does not render ComedianAdvancedFilters for non-comedian variants", () => {
        const { container } = render(
            <FilterModal
                filters={[aliasFilter]}
                total={42}
                variant={SearchVariant.AllShows}
            />,
        );
        expect(
            container.querySelector(
                '[data-testid="comedian-advanced-filters"]',
            ),
        ).toBeNull();
    });

    it("renders the live total count in the footer button", () => {
        const { container } = render(
            <FilterModal
                filters={[aliasFilter]}
                total={123}
                variant={SearchVariant.AllComedians}
            />,
        );
        const button = container.querySelector("button.bg-copper");
        expect(button?.textContent).toContain("123");
    });
});
