import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { middleware, setParamDefaults } from "./middleware";
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

        expect(params.get(QueryProperty.Size)).toBe("20");
    });

    it("does not override explicit page sizes on comedian detail pages", () => {
        const params = setParamDefaults(
            new URLSearchParams("size=20"),
            "/comedian/Taylor-Tomlinson",
        );

        expect(params.get(QueryProperty.Size)).toBe("20");
    });
});

describe("middleware SEO headers", () => {
    it("adds noindex to non-canonical hosts", async () => {
        const response = await middleware(
            new NextRequest("https://laughtrack.vercel.app/club/search"),
        );

        expect(response.headers.get("X-Robots-Tag")).toBe("noindex");
    });

    it("does not add noindex to canonical hosts", async () => {
        const response = await middleware(
            new NextRequest("https://www.laugh-track.com/club/search"),
        );

        expect(response.headers.get("X-Robots-Tag")).toBeNull();
    });
});
