import { describe, it, expect } from "vitest";
import { Prisma } from "@prisma/client";
import { QueryHelper } from "./QueryHelper";

function makeHelper(
    params: Record<string, string | undefined> = {},
    slug?: string,
) {
    return new QueryHelper({
        params,
        timezone: "America/New_York",
        slug,
    });
}

describe("QueryHelper.getClubNameClause", () => {
    it("returns empty object when club param is absent", () => {
        expect(makeHelper({}).getClubNameClause()).toEqual({});
    });

    it("returns empty object when club param is empty string", () => {
        expect(makeHelper({ club: "" }).getClubNameClause()).toEqual({});
    });

    describe("search-page context (contains match)", () => {
        it("returns insensitive contains clause for a free-text club query", () => {
            const clause = makeHelper({ club: "helium" }).getClubNameClause();
            expect(clause).toEqual({
                name: {
                    contains: "helium",
                    mode: Prisma.QueryMode.insensitive,
                },
            });
        });

        it("does not switch to exact-match just because the param is set via constructor", () => {
            // The URL slug could be present (e.g. comedian detail page) but
            // setClubName() has not been called, so substring semantics apply.
            const clause = makeHelper(
                { club: "The Stand" },
                "some-other-slug",
            ).getClubNameClause();
            expect(clause).toEqual({
                name: {
                    contains: "The Stand",
                    mode: Prisma.QueryMode.insensitive,
                },
            });
        });
    });

    describe("detail-page context (exact match after setClubName)", () => {
        it("returns insensitive equals clause after setClubName", () => {
            const helper = makeHelper({}, "The Stand");
            helper.setClubName();
            expect(helper.getClubNameClause()).toEqual({
                name: {
                    equals: "The Stand",
                    mode: Prisma.QueryMode.insensitive,
                },
            });
        });

        it("does not match clubs whose names merely contain the slug as a substring", () => {
            // Regression guard: /club/The Stand must not leak shows from
            // "The Stand Up Comedy Club" (which would inject its 9831 Belmont
            // St address into The Stand NYC's show cards).
            const helper = makeHelper({}, "The Stand");
            helper.setClubName();
            const clause = helper.getClubNameClause() as {
                name: { equals?: string; contains?: string };
            };
            expect(clause.name.equals).toBe("The Stand");
            expect(clause.name.contains).toBeUndefined();
        });

        it("decodes URL-encoded slugs before emitting the clause", () => {
            const helper = makeHelper({}, "The%20Stand");
            helper.setClubName();
            const clause = helper.getClubNameClause() as {
                name: { equals?: string };
            };
            expect(clause.name.equals).toBe("The Stand");
        });

        it("emits empty equals when setClubName is called with no slug", () => {
            // Safety: a missing slug should not degrade to substring matching
            // (which would match every club).
            const helper = makeHelper();
            helper.setClubName();
            expect(helper.getClubNameClause()).toEqual({});
        });
    });
});
