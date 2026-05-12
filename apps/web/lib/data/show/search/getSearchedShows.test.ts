import { describe, it, expect, vi, beforeEach } from "vitest";
import { FREE_FILTER_SLUG } from "@/objects/class/query/QueryHelper";
import { ParameterizedRequestData } from "@/objects/interface";

const { mockFindShowsWithCount, mockGetFilters } = vi.hoisted(() => ({
    mockFindShowsWithCount: vi.fn(),
    mockGetFilters: vi.fn(),
}));

vi.mock("./findShowsWithCount", () => ({
    findShowsWithCount: mockFindShowsWithCount,
}));
vi.mock("../../filters/getFilters", () => ({
    getFilters: mockGetFilters,
}));

import { getSearchedShows } from "./getSearchedShows";

function buildRequest(filters?: string): ParameterizedRequestData {
    return {
        params: filters !== undefined ? { filters } : {},
        timezone: "America/New_York",
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindShowsWithCount.mockResolvedValue({
        shows: [],
        totalCount: 0,
        zipCapTriggered: false,
    });
    mockGetFilters.mockResolvedValue([]);
});

describe("getSearchedShows — synthetic Free filter (TASK-2141)", () => {
    it("injects a Free FilterDTO into the response.filters even when no tag filters exist", async () => {
        mockGetFilters.mockResolvedValue([]);

        const response = await getSearchedShows(buildRequest());

        expect(response.filters).toHaveLength(1);
        expect(response.filters[0]).toMatchObject({
            slug: FREE_FILTER_SLUG,
            name: "Free",
        });
    });

    it("marks the Free FilterDTO selected:true when 'free' is the only slug in filters CSV", async () => {
        mockGetFilters.mockResolvedValue([]);

        const response = await getSearchedShows(buildRequest(FREE_FILTER_SLUG));

        const free = response.filters.find((f) => f.slug === FREE_FILTER_SLUG);
        expect(free?.selected).toBe(true);
    });

    it("marks the Free FilterDTO selected:true when 'free' is mixed with other slugs", async () => {
        mockGetFilters.mockResolvedValue([
            { id: 10, slug: "open-mic", name: "Open Mic", selected: true },
        ]);

        const response = await getSearchedShows(
            buildRequest(`open-mic,${FREE_FILTER_SLUG}`),
        );

        const free = response.filters.find((f) => f.slug === FREE_FILTER_SLUG);
        expect(free?.selected).toBe(true);
    });

    it("marks the Free FilterDTO selected:false when filters is empty", async () => {
        const response = await getSearchedShows(buildRequest());

        const free = response.filters.find((f) => f.slug === FREE_FILTER_SLUG);
        expect(free?.selected).toBe(false);
    });

    it("does NOT mark Free selected for a substring-only match (e.g. 'freestyle')", async () => {
        // Regression guard for the desync bug a substring check would cause.
        // The where-clause logic uses exact-match; the chip's selected flag
        // must too, otherwise the Free chip lights up for unrelated tags.
        mockGetFilters.mockResolvedValue([
            { id: 22, slug: "freestyle", name: "Freestyle", selected: true },
        ]);

        const response = await getSearchedShows(buildRequest("freestyle"));

        const free = response.filters.find((f) => f.slug === FREE_FILTER_SLUG);
        expect(free?.selected).toBe(false);
    });

    it("merges the synthetic Free filter with real tag filters and sorts alphabetically by name", async () => {
        mockGetFilters.mockResolvedValue([
            { id: 1, slug: "weekly", name: "Weekly" },
            { id: 2, slug: "open-mic", name: "Open Mic" },
            { id: 3, slug: "headliner", name: "Headliner" },
        ]);

        const response = await getSearchedShows(buildRequest());

        expect(response.filters.map((f) => f.name)).toEqual([
            "Free",
            "Headliner",
            "Open Mic",
            "Weekly",
        ]);
    });

    it("forwards totalCount, data, and zipCapTriggered from findShowsWithCount", async () => {
        mockFindShowsWithCount.mockResolvedValue({
            shows: [{ id: 1 }, { id: 2 }],
            totalCount: 42,
            zipCapTriggered: true,
        });

        const response = await getSearchedShows(buildRequest());

        expect(response.total).toBe(42);
        expect(response.data).toHaveLength(2);
        expect(response.zipCapTriggered).toBe(true);
    });
});
