import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            groupBy: vi.fn(),
        },
    },
}));

import {
    getComedianHomeCityFilters,
    MIN_COMEDIANS_PER_HOME_CITY,
} from "./getComedianHomeCityFilters";
import { db } from "@/lib/db";

const mockGroupBy = vi.mocked(db.comedian.groupBy);

function group(homeCity: string | null, homeState: string | null, n: number) {
    return { homeCity, homeState, _count: { _all: n } };
}

describe("getComedianHomeCityFilters", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("returns [] when no comedian has a home city", async () => {
        mockGroupBy.mockResolvedValue([] as never);
        expect(await getComedianHomeCityFilters()).toEqual([]);
    });

    it("builds city|state tokens and 'City, State' labels, ordered by count desc", async () => {
        mockGroupBy.mockResolvedValue([
            group("Chicago", "IL", 30),
            group("New York", "NY", 100),
            group("Austin", "TX", 50),
        ] as never);

        const result = await getComedianHomeCityFilters();

        expect(result).toEqual([
            { value: "New York|NY", label: "New York, NY", count: 100 },
            { value: "Austin|TX", label: "Austin, TX", count: 50 },
            { value: "Chicago|IL", label: "Chicago, IL", count: 30 },
        ]);
    });

    it("keeps same-named cities in different states distinct", async () => {
        mockGroupBy.mockResolvedValue([
            group("Arlington", "TX", 20),
            group("Arlington", "VA", 9),
        ] as never);

        const result = await getComedianHomeCityFilters();

        expect(result.map((r) => r.value)).toEqual([
            "Arlington|TX",
            "Arlington|VA",
        ]);
    });

    it("drops cities below the minimum-count threshold", async () => {
        mockGroupBy.mockResolvedValue([
            group("New York", "NY", MIN_COMEDIANS_PER_HOME_CITY),
            group("Tinytown", "ND", MIN_COMEDIANS_PER_HOME_CITY - 1),
        ] as never);

        const result = await getComedianHomeCityFilters();

        expect(result.map((r) => r.label)).toEqual(["New York, NY"]);
    });

    it("merges NULL-state and empty-string-state rows for the same city into one option with summed count", async () => {
        mockGroupBy.mockResolvedValue([
            group("London", null, 25),
            group("London", "", 18),
        ] as never);

        const result = await getComedianHomeCityFilters();

        // One option (no React dup-key), count is the merged population.
        expect(result).toEqual([
            { value: "London", label: "London", count: 43 },
        ]);
    });

    it("ignores rows with a blank city and falls back to a city-only token when state is blank", async () => {
        mockGroupBy.mockResolvedValue([
            group("   ", "NY", 99), // blank city → dropped
            group("London", null, 40), // no state → city-only token + label
            group("Paris", "", 12), // empty-string state → treated as null
        ] as never);

        const result = await getComedianHomeCityFilters();

        expect(result).toEqual([
            { value: "London", label: "London", count: 40 },
            { value: "Paris", label: "Paris", count: 12 },
        ]);
    });
});
