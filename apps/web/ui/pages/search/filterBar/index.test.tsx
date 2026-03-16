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
vi.mock("@/ui/components/params/search/pages/show/all", () => ({
    default: () => <div data-testid="show-all-search" />,
}));
vi.mock("@/util/sort", () => ({
    getSortOptionsForEntityType: () => [],
}));

describe("FilterBar", () => {
    it.each(allVariantTypes)(
        "renders without error for variant %s",
        (variant) => {
            expect(() =>
                render(<FilterBar variant={variant} total={0} filters={0} />),
            ).not.toThrow();
        },
    );

    it("renders the sort component for every variant", () => {
        for (const variant of allVariantTypes) {
            const { container, unmount } = render(
                <FilterBar variant={variant} total={5} filters={0} />,
            );
            expect(
                container.querySelector('[data-testid="sort-param"]'),
            ).not.toBeNull();
            unmount();
        }
    });

    it("renders FilterModalButton when filters > 0", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllShows}
                total={10}
                filters={3}
            />,
        );
        expect(
            container.querySelector('[data-testid="filter-modal-button"]'),
        ).not.toBeNull();
    });

    it("does not render FilterModalButton when filters is 0", () => {
        const { container } = render(
            <FilterBar
                variant={SearchVariant.AllShows}
                total={10}
                filters={0}
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
                filters={0}
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
                filters={0}
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
                filters={0}
            />,
        );
        expect(
            container.querySelector('[data-testid="comedian-all-search"]'),
        ).not.toBeNull();
    });
});
