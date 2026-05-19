import { describe, it, expect } from "vitest";
import { getSortOptionsForEntityType } from "./index";
import { EntityType, SortParamValue } from "../../objects/enum";

describe("getSortOptionsForEntityType", () => {
    describe("EntityType.Comedian", () => {
        const options = getSortOptionsForEntityType(EntityType.Comedian);

        it("first option (UI default) is 'Most Popular' / PopularityDesc", () => {
            expect(options[0]).toEqual({
                name: "Most Popular",
                value: SortParamValue.PopularityDesc,
            });
        });

        it("exposes the four iOS-aligned axes and nothing else", () => {
            expect(options.map((o) => o.value)).toEqual([
                SortParamValue.PopularityDesc,
                SortParamValue.PopularityAsc,
                SortParamValue.NameAsc,
                SortParamValue.NameDesc,
            ]);
        });

        it("does not surface scraping-derived activity axes to public users", () => {
            const values = options.map((o) => o.value);
            expect(values).not.toContain(SortParamValue.ActivityDesc);
            expect(values).not.toContain(SortParamValue.ActivityAsc);
            expect(values).not.toContain(SortParamValue.ShowCountDesc);
            expect(values).not.toContain(SortParamValue.ShowCountAsc);
        });
    });

    describe("EntityType.Club", () => {
        const options = getSortOptionsForEntityType(EntityType.Club);

        it("first option (UI default) is 'Most Active' / TotalShowsDesc", () => {
            expect(options[0]).toEqual({
                name: "Most Active",
                value: SortParamValue.TotalShowsDesc,
            });
        });

        it("includes 'Least Active' / TotalShowsAsc", () => {
            const opt = options.find((o) => o.name === "Least Active");
            expect(opt?.value).toBe(SortParamValue.TotalShowsAsc);
        });

        it("includes A-Z and Z-A options for user opt-in", () => {
            const values = options.map((o) => o.value);
            expect(values).toContain(SortParamValue.NameAsc);
            expect(values).toContain(SortParamValue.NameDesc);
        });
    });

    describe("default case (Show/other)", () => {
        const options = getSortOptionsForEntityType(EntityType.Show);

        it("exposes the five iOS-aligned show axes and nothing else", () => {
            expect(options.map((o) => o.value)).toEqual([
                SortParamValue.DateAsc,
                SortParamValue.DateDesc,
                SortParamValue.PopularityDesc,
                SortParamValue.PriceAsc,
                SortParamValue.PriceDesc,
            ]);
        });

        it("does not surface PopularityAsc, NameAsc, or NameDesc to public users", () => {
            const values = options.map((o) => o.value);
            expect(values).not.toContain(SortParamValue.PopularityAsc);
            expect(values).not.toContain(SortParamValue.NameAsc);
            expect(values).not.toContain(SortParamValue.NameDesc);
        });
    });

    describe("EntityType.Podcast", () => {
        const options = getSortOptionsForEntityType(EntityType.Podcast);

        it("first option (UI default) is 'Most Episodes' / ShowCountDesc", () => {
            expect(options[0]).toEqual({
                name: "Most Episodes",
                value: SortParamValue.ShowCountDesc,
            });
        });

        it("exposes the four iOS-aligned axes and nothing else", () => {
            expect(options.map((o) => o.value)).toEqual([
                SortParamValue.ShowCountDesc,
                SortParamValue.ShowCountAsc,
                SortParamValue.NameAsc,
                SortParamValue.NameDesc,
            ]);
        });

        it("does not surface scraping-derived activity or freshness axes to public users", () => {
            const values = options.map((o) => o.value);
            expect(values).not.toContain(SortParamValue.ActivityDesc);
            expect(values).not.toContain(SortParamValue.ActivityAsc);
            expect(values).not.toContain(SortParamValue.InsertedAtDesc);
            expect(values).not.toContain(SortParamValue.InsertedAtAsc);
        });
    });
});
