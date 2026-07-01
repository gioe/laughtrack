/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import FilterBar from "./index";
import { SearchVariant, allVariantTypes } from "@/objects/enum/searchVariant";

vi.mock("@/ui/components/params/filter", () => ({
    FilterModalButton: () => <div data-testid="filter-modal-button" />,
}));
vi.mock("@/ui/components/params/page", () => ({
    PageParamComponent: () => <div data-testid="page-param" />,
}));
vi.mock("@/ui/components/params/sort", () => ({
    SortParamComponent: () => <div data-testid="sort-param" />,
}));
vi.mock("@/ui/components/params/search/pages/club/all", () => ({
    default: () => <div data-testid="club-all-search" />,
}));
vi.mock("@/ui/components/params/search/pages/club/detail", () => ({
    default: () => <div data-testid="club-detail-search" />,
}));
vi.mock("@/ui/components/params/search/pages/comedian/all", () => ({
    default: () => <div data-testid="comedian-all-search" />,
}));
vi.mock("@/ui/components/params/search/pages/comedian/detail", () => ({
    default: () => <div data-testid="comedian-detail-search" />,
}));
vi.mock("@/ui/components/params/search/pages/podcast/all", () => ({
    default: () => <div data-testid="podcast-all-search" />,
}));
vi.mock("@/ui/components/params/search/pages/show/all", () => ({
    default: () => <div data-testid="show-all-search" />,
}));
vi.mock("@/util/sort", () => ({
    getSortOptionsForEntityType: () => [],
}));
vi.mock("@/hooks/useUrlParams", () => ({
    useUrlParams: () => ({
        getTypedParam: () => "",
        setTypedParam: vi.fn(),
        setMultipleTypedParams: vi.fn(),
    }),
}));

describe("FilterBar", () => {
    it.each(allVariantTypes)(
        "renders without error for variant %s",
        (variant) => {
            const { container } = render(
                <FilterBar variant={variant} total={0} filterData={[]} />,
            );
            // Every variant must produce at least some DOM output
            expect(container.firstChild).not.toBeNull();
        },
    );

    it("renders the sort component for every variant", () => {
        for (const variant of allVariantTypes) {
            const { container, unmount } = render(
                <FilterBar variant={variant} total={5} filterData={[]} />,
            );
            expect(
                container.querySelector('[data-testid="sort-param"]'),
            ).not.toBeNull();
            unmount();
        }
    });

    it("renders FilterModalButton when filterData has items", () => {
        const mockFilters = [
            { id: 1, slug: "late-night", name: "Late Night" },
            { id: 2, slug: "family", name: "Family Friendly" },
            { id: 3, slug: "improv", name: "Improv" },
        ];
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllShows}
                total={10}
                filterData={mockFilters}
            />,
        );
        expect(
            container.querySelector('[data-testid="filter-modal-button"]'),
        ).not.toBeNull();
    });

    it("does not render FilterModalButton when filterData is empty", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllShows}
                total={10}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="filter-modal-button"]'),
        ).toBeNull();
    });

    it("renders the correct search bar for AllClubs", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllClubs}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="club-all-search"]'),
        ).not.toBeNull();
    });

    it("renders the correct search bar for AllShows", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllShows}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="show-all-search"]'),
        ).not.toBeNull();
    });

    it("renders the correct search bar for AllComedians", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllComedians}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="comedian-all-search"]'),
        ).not.toBeNull();
    });

    it("renders the correct search bar for ClubDetail", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="club-detail-search"]'),
        ).not.toBeNull();
    });

    it("renders the correct search bar for ComedianDetail", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.ComedianDetail}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="comedian-detail-search"]'),
        ).not.toBeNull();
    });

    it("renders the correct search bar for AllPodcasts", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllPodcasts}
                total={5}
                filterData={[]}
            />,
        );
        expect(
            container.querySelector('[data-testid="podcast-all-search"]'),
        ).not.toBeNull();
    });

    it("renders the FilterModalButton for AllPodcasts even without tag filters", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllPodcasts}
                total={5}
                filterData={[]}
            />,
        );

        expect(
            container.querySelector('[data-testid="filter-modal-button"]'),
        ).not.toBeNull();
    });

    describe("home-city filter", () => {
        const homeCityFilters = [
            { value: "New York|NY", label: "New York, NY", count: 100 },
            { value: "Austin|TX", label: "Austin, TX", count: 50 },
        ];

        it("renders the home-city select with options on AllComedians", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllComedians}
                    total={5}
                    filterData={[]}
                    homeCityFilters={homeCityFilters}
                />,
            );
            const select = container.querySelector(
                'select[aria-label="Filter by home city"]',
            );
            expect(select).not.toBeNull();
            const options = select?.querySelectorAll("option");
            // "All home cities" sentinel + one per city.
            expect(options?.length).toBe(homeCityFilters.length + 1);
            expect(select?.textContent).toContain("New York, NY (100)");
            expect(select?.textContent).toContain("Austin, TX (50)");
        });

        it("omits the home-city select when no home-location data is available", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllComedians}
                    total={5}
                    filterData={[]}
                    homeCityFilters={[]}
                />,
            );
            expect(
                container.querySelector(
                    'select[aria-label="Filter by home city"]',
                ),
            ).toBeNull();
        });

        it("does not render the home-city select on non-comedian variants", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllClubs}
                    total={5}
                    filterData={[]}
                    homeCityFilters={homeCityFilters}
                />,
            );
            expect(
                container.querySelector(
                    'select[aria-label="Filter by home city"]',
                ),
            ).toBeNull();
        });
    });

    describe("home-club filter", () => {
        const homeClubFilters = [
            { value: "20", label: "Comedy Store", count: 12 },
            { value: "10", label: "The Setup", count: 4 },
        ];

        it("renders the home-club select with options on AllComedians", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllComedians}
                    total={5}
                    filterData={[]}
                    homeClubFilters={homeClubFilters}
                />,
            );
            const select = container.querySelector(
                'select[aria-label="Filter by home club"]',
            );
            expect(select).not.toBeNull();
            const options = select?.querySelectorAll("option");
            // "All home clubs" sentinel + one per club.
            expect(options?.length).toBe(homeClubFilters.length + 1);
            expect(select?.textContent).toContain("Comedy Store (12)");
            expect(select?.textContent).toContain("The Setup (4)");
        });

        it("omits the home-club select when no home-club data is available", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllComedians}
                    total={5}
                    filterData={[]}
                    homeClubFilters={[]}
                />,
            );
            expect(
                container.querySelector(
                    'select[aria-label="Filter by home club"]',
                ),
            ).toBeNull();
        });

        it("does not render the home-club select on non-comedian variants", () => {
            const { container } = render(
                <FilterBar
                    variant={SearchVariant.AllClubs}
                    total={5}
                    filterData={[]}
                    homeClubFilters={homeClubFilters}
                />,
            );
            expect(
                container.querySelector(
                    'select[aria-label="Filter by home club"]',
                ),
            ).toBeNull();
        });
    });
});
