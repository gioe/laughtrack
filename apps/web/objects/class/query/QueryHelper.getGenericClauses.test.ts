import { describe, it, expect } from "vitest";
import { QueryHelper } from "./QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";

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
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("total_shows_asc", () => {
        it("sets primary sort to totalShows asc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsAsc,
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ totalShows: "asc" }, ...TIEBREAKER]);
        });
    });

    describe("total_shows_desc", () => {
        it("sets primary sort to totalShows desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.TotalShowsDesc,
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("show_count_asc", () => {
        it("sets primary sort to totalShows asc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountAsc,
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ totalShows: "asc" }, ...TIEBREAKER]);
        });
    });

    describe("show_count_desc", () => {
        it("sets primary sort to totalShows desc with tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.ShowCountDesc,
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ totalShows: "desc" }, ...TIEBREAKER]);
        });
    });

    describe("name_asc", () => {
        it("sets primary sort to name asc with no tiebreaker", () => {
            const { orderBy } = makeHelper(
                SortParamValue.NameAsc,
            ).getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ name: "asc" }]);
        });
    });

    describe("invalid sort param", () => {
        it("falls back to popularity_desc with tiebreaker", () => {
            const { orderBy } =
                makeHelper("not_a_valid_sort").getGenericClauses(TOTAL);
            expect(orderBy).toEqual([{ popularity: "desc" }, ...TIEBREAKER]);
        });
    });
});
