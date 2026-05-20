/**
 * @vitest-environment happy-dom
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { cleanup, render } from "@testing-library/react";

const { mockGetSearchedPodcasts } = vi.hoisted(() => ({
    mockGetSearchedPodcasts: vi.fn().mockResolvedValue({
        data: [],
        total: 0,
        filters: [],
    }),
}));

vi.mock("@/lib/data/podcast/search/getSearchedPodcasts", () => ({
    getSearchedPodcasts: mockGetSearchedPodcasts,
}));

vi.mock("next/cache", () => ({
    unstable_cache: <T,>(fn: () => Promise<T>) => fn,
}));

vi.mock("@/ui/components/JsonLd", () => ({
    default: () => <div data-testid="json-ld" />,
}));

vi.mock("@/ui/pages/search/header", () => ({
    default: ({ title }: { title: string }) => (
        <div data-testid="search-header">{title}</div>
    ),
}));

vi.mock("@/ui/pages/search/podcast/PodcastSearchClient", () => ({
    default: () => <div data-testid="podcast-search-client" />,
}));

vi.mock("@/ui/pages/search/filterBar", () => ({
    default: ({
        variant,
        total,
        filterData,
    }: {
        variant: string | number;
        total: number;
        filterData: unknown[];
    }) => (
        <div
            data-testid="filter-bar"
            data-variant={String(variant)}
            data-total={total}
            data-filter-count={filterData.length}
        >
            <button type="button">Sort</button>
            <button type="button">Filter</button>
            <label>
                <input type="checkbox" />
                Include all
            </label>
            <span>{total} results</span>
        </div>
    ),
}));

vi.mock("@/ui/components/modals/filter", () => ({
    default: ({
        filters,
        total,
    }: {
        filters: unknown[];
        total: number;
    }) => (
        <div
            data-testid="filter-modal"
            data-filter-count={filters.length}
            data-total={total}
        />
    ),
}));

vi.mock("@/util/jsonLd", () => ({
    buildPodcastCollectionJsonLd: () => ({}),
}));

import PodcastsPage from "@/app/(entities)/(collection)/podcast/search/page";
import { SearchVariant } from "@/objects/enum/searchVariant";

beforeEach(() => {
    cleanup();
    mockGetSearchedPodcasts.mockClear();
});

describe("PodcastsPage filter shell integration", () => {
    it("renders the shared FilterBar with the AllPodcasts variant", async () => {
        const tree = await PodcastsPage({
            searchParams: Promise.resolve({}),
        });
        const { container } = render(tree);

        const filterBar = container.querySelector(
            '[data-testid="filter-bar"]',
        );
        expect(filterBar).not.toBeNull();
        expect(filterBar?.getAttribute("data-variant")).toBe(
            String(SearchVariant.AllPodcasts),
        );
        expect(container.querySelector("button")).not.toBeNull();
        expect(container.textContent).toContain("Sort");
        expect(container.textContent).toContain("Filter");
        expect(container.textContent).toContain("Include all");
        expect(container.textContent).toContain("0 results");
    });

    it("renders the shared FilterModal alongside the FilterBar", async () => {
        const tree = await PodcastsPage({
            searchParams: Promise.resolve({}),
        });
        const { container } = render(tree);

        expect(
            container.querySelector('[data-testid="filter-modal"]'),
        ).not.toBeNull();
    });

    it("threads sort and includeEmpty params into getSearchedPodcasts", async () => {
        const tree = await PodcastsPage({
            searchParams: Promise.resolve({
                q: "comedy",
                sort: "name_asc",
                includeEmpty: "true",
            }),
        });
        render(tree);

        expect(mockGetSearchedPodcasts).toHaveBeenCalledWith({
            q: "comedy",
            sort: "name_asc",
            includeEmpty: "true",
        });
    });

    it("does not render the legacy standalone Search button", async () => {
        const tree = await PodcastsPage({
            searchParams: Promise.resolve({}),
        });
        const { container } = render(tree);

        const submitButtons = container.querySelectorAll(
            'button[type="submit"]',
        );
        expect(submitButtons.length).toBe(0);
    });
});
