import { describe, expect, it } from "vitest";
import { setParamDefaults } from "./middleware";
import { QueryProperty } from "./objects/enum";

describe("setParamDefaults", () => {
    it("uses a smaller default page size for comedian detail pages", () => {
        const params = setParamDefaults(
            new URLSearchParams(),
            "/comedian/Taylor-Tomlinson",
        );

        expect(params.get(QueryProperty.Size)).toBe("5");
    });

    it("keeps the standard default page size for comedian search", () => {
        const params = setParamDefaults(
            new URLSearchParams(),
            "/comedian/search",
        );

        expect(params.get(QueryProperty.Size)).toBe("10");
    });

    it("does not override explicit page sizes on comedian detail pages", () => {
        const params = setParamDefaults(
            new URLSearchParams("size=20"),
            "/comedian/Taylor-Tomlinson",
        );

        expect(params.get(QueryProperty.Size)).toBe("20");
    });
});
