import { describe, it, expect } from "vitest";
import {
    QueryHelper,
    SHOW_SORT_MAP,
    COMEDIAN_SORT_MAP,
    CLUB_SORT_MAP,
} from "./QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";

// COMEDIAN_SORT_MAP is used as a representative map for tests that are not
// entity-specific — it covers popularity, totalShows, name, and activity fields.
const TEST_SORT_MAP = COMEDIAN_SORT_MAP;

const TIEBREAKER = [{ name: "asc" }];

function makeHelper(sort: string): QueryHelper {
    return new QueryHelper({
        params: { sort },
        timezone: "America/New_York",
    });
}

describe("QueryHelper.getGenericClauses — orderBy output", () => {
    const TOTAL = 100;

    describe("popularity_desc (default)", () => {
        it("sets primary sort to popularity desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.PopularityDesc,
            ).getGenericClauses(TOTAL, TEST_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("total_shows_asc", () => {
        it("sets primary sort to totalShows asc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsAsc,
            ).getGenericClauses(TOTAL, TEST_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "asc" }, ...TIEBREAKER]);
        });
    });

    describe("total_shows_desc", () => {
        it("sets primary sort to totalShows desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsDesc,
            ).getGenericClauses(TOTAL, TEST_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("show_count_asc", () => {
        it("sets primary sort to totalShows asc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountAsc,
            ).getGenericClauses(TOTAL, CLUB_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "asc" }, ...TIEBREAKER]);
        });
    });

    describe("show_count_desc", () => {
        it("sets primary sort to totalShows desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountDesc,
            ).getGenericClauses(TOTAL, CLUB_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("name_asc", () => {
        it("sets primary sort to name asc with no tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.NameAsc,
            ).getGenericClauses(TOTAL, TEST_SORT_MAP);
            expect(orderBy).toEqual([{ name: "asc" }]);
        });
    });

    describe("invalid sort param", () => {
        it("falls back to popularity_desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                "not_a_valid_sort",
            ).getGenericClauses(TOTAL, TEST_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });
});

describe("QueryHelper.getGenericClauses — per-entity sort maps", () => {
    const TOTAL = 100;

    describe("SHOW_SORT_MAP", () => {
        it("allows date_asc sort for shows", () => {
            const { orderBy } = makeHelper(
                SortParamValue.DateAsc,
            ).getGenericClauses(TOTAL, SHOW_SORT_MAP);
            expect(orderBy).toEqual([{ date: "asc" }, ...TIEBREAKER]);
        });

        it("falls back to popularity_desc for totalShows sort (not a Show field)", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsDesc,
            ).getGenericClauses(TOTAL, SHOW_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });

        it("falls back to popularity_desc for show_count sort (not a Show field)", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountAsc,
            ).getGenericClauses(TOTAL, SHOW_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("COMEDIAN_SORT_MAP", () => {
        it("allows totalShows sort for comedians", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsDesc,
            ).getGenericClauses(TOTAL, COMEDIAN_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });

        it("falls back to popularity_desc for date sort (not a Comedian field)", () => {
            const { orderBy } = makeHelper(
                SortParamValue.DateAsc,
            ).getGenericClauses(TOTAL, COMEDIAN_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("CLUB_SORT_MAP", () => {
        it("allows totalShows sort for clubs", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsAsc,
            ).getGenericClauses(TOTAL, CLUB_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "asc" }, ...TIEBREAKER]);
        });

        it("allows show_count sort for clubs", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountDesc,
            ).getGenericClauses(TOTAL, CLUB_SORT_MAP);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });

        it("falls back to popularity_desc for date sort (not a Club field)", () => {
            const { orderBy } = makeHelper(
                SortParamValue.DateDesc,
            ).getGenericClauses(TOTAL, CLUB_SORT_MAP);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });
});
