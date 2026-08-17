/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import FilterModal from "./index";
import { SearchVariant } from "@/objects/enum/searchVariant";

const mockModalOnClose = vi.fn();
const mockHandleClose = vi.fn();

vi.mock("@/hooks", () => ({
    useFilterModal: () => ({ isOpen: true, onClose: mockModalOnClose }),
    useDialogKeyboard: () => {},
}));
vi.mock("@/hooks/useFilters", () => ({
    useFilters: () => ({
        handleOpen: vi.fn(),
        handleFilterChange: vi.fn(),
        handleClose: mockHandleClose,
        selections: [],
    }),
}));

beforeEach(() => {
    mockModalOnClose.mockClear();
    mockHandleClose.mockClear();
});
// Replace the rich children with sentinels so we don't depend on their full
// dependency graph (zip resolution, calendar popover, etc.) in unit tests.
vi.mock("./comedianAdvanced", () => ({
    default: () => <div data-testid="comedian-advanced-filters" />,
}));
vi.mock("@/ui/components/club/clubProgrammingFilters", () => ({
    default: () => <div data-testid="club-programming-filters" />,
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

    it("keeps the primary show facets inside the filter modal", () => {
        const showFilters = [
            { id: -1, slug: "free", name: "Free" },
            { id: 1, slug: "open_mic", name: "Open mic" },
            { id: 2, slug: "standup", name: "Stand-up" },
            { id: 3, slug: "improv", name: "Improv" },
        ];
        const { container } = render(
            <FilterModal
                filters={showFilters}
                total={42}
                variant={SearchVariant.AllShows}
            />,
        );

        for (const filter of showFilters) {
            expect(
                container.querySelector(`[data-testid="chip-${filter.name}"]`),
            ).not.toBeNull();
        }
    });

    it("retains ClubProgrammingFilters for AllClubs", () => {
        const { container } = render(
            <FilterModal
                filters={[]}
                total={42}
                variant={SearchVariant.AllClubs}
            />,
        );
        expect(
            container.querySelector('[data-testid="club-programming-filters"]'),
        ).not.toBeNull();
    });

    it("does not expose the duplicate Podcast Scope control", () => {
        const { container } = render(
            <FilterModal
                filters={[]}
                total={42}
                variant={SearchVariant.AllPodcasts}
            />,
        );

        expect(container.textContent).not.toContain("Podcast Scope");
        expect(container.textContent).not.toContain("Include all podcasts");
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

    it("Show Results button applies selections without reverting (does not call handleClose)", () => {
        const { container } = render(
            <FilterModal filters={[aliasFilter]} total={42} />,
        );
        const applyButton = container.querySelector(
            "button.bg-copper",
        ) as HTMLButtonElement;
        fireEvent.click(applyButton);
        expect(mockHandleClose).not.toHaveBeenCalled();
        expect(mockModalOnClose).toHaveBeenCalledTimes(1);
    });

    it("X button cancels and reverts selections (calls handleClose)", () => {
        const { container } = render(
            <FilterModal filters={[aliasFilter]} total={42} />,
        );
        const closeButton = container.querySelector(
            'button[aria-label="Close dialog"]',
        ) as HTMLButtonElement;
        fireEvent.click(closeButton);
        expect(mockHandleClose).toHaveBeenCalledTimes(1);
        expect(mockModalOnClose).toHaveBeenCalledTimes(1);
    });
});
