import { describe, it, expect } from "vitest";
import { getSortOptionsForEntityType } from "./index";
import { EntityType, SortParamValue } from "../../objects/enum";

describe("getSortOptionsForEntityType", () => {
    describe("EntityType.Comedian", () => {
        const options = getSortOptionsForEntityType(EntityType.Comedian);

        it("'Most Active' maps to ActivityDesc", () => {
            const opt = options.find((o) => o.name === "Most Active");
            expect(opt).toBeDefined();
            expect(opt?.value).toBe(SortParamValue.ActivityDesc);
        });

        it("'Least Active' maps to ActivityAsc", () => {
            const opt = options.find((o) => o.name === "Least Active");
            expect(opt).toBeDefined();
            expect(opt?.value).toBe(SortParamValue.ActivityAsc);
        });

        it("'Most Popular' maps to PopularityDesc", () => {
            const opt = options.find((o) => o.name === "Most Popular");
            expect(opt).toBeDefined();
            expect(opt?.value).toBe(SortParamValue.PopularityDesc);
        });

        it("'Least Popular' maps to PopularityAsc", () => {
            const opt = options.find((o) => o.name === "Least Popular");
            expect(opt).toBeDefined();
            expect(opt?.value).toBe(SortParamValue.PopularityAsc);
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

        it("includes date sort options", () => {
            const values = options.map((o) => o.value);
            expect(values).toContain(SortParamValue.DateAsc);
            expect(values).toContain(SortParamValue.DateDesc);
        });

        it("includes popularity sort options", () => {
            const values = options.map((o) => o.value);
            expect(values).toContain(SortParamValue.PopularityDesc);
            expect(values).toContain(SortParamValue.PopularityAsc);
        });

        it("includes price sort options", () => {
            const values = options.map((o) => o.value);
            expect(values).toContain(SortParamValue.PriceAsc);
            expect(values).toContain(SortParamValue.PriceDesc);
        });
    });
});
