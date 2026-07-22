import { describe, expect, it } from "vitest";
import { recalculatePopularityForInstagramFollowers } from "./comedianPopularity";

describe("recalculatePopularityForInstagramFollowers", () => {
    it("adds the canonical Instagram social contribution when it is the only platform", () => {
        expect(
            recalculatePopularityForInstagramFollowers({
                popularity: 0.2,
                previousInstagramFollowers: null,
                nextInstagramFollowers: 5_000_000,
                tiktokFollowers: null,
                youtubeFollowers: null,
            }),
        ).toBe(0.4);
    });

    it("renormalizes the social contribution across every populated platform", () => {
        expect(
            recalculatePopularityForInstagramFollowers({
                popularity: 0.4,
                previousInstagramFollowers: null,
                nextInstagramFollowers: 5_000_000,
                tiktokFollowers: 25_000_000,
                youtubeFollowers: 2_500_000,
            }),
        ).toBe(0.4);
    });

    it("removes a stale Instagram contribution and clamps canonical bounds", () => {
        expect(
            recalculatePopularityForInstagramFollowers({
                popularity: 0.4,
                previousInstagramFollowers: 10_000_000,
                nextInstagramFollowers: null,
                tiktokFollowers: null,
                youtubeFollowers: null,
            }),
        ).toBe(0);

        expect(
            recalculatePopularityForInstagramFollowers({
                popularity: 0.9,
                previousInstagramFollowers: null,
                nextInstagramFollowers: 20_000_000,
                tiktokFollowers: null,
                youtubeFollowers: null,
            }),
        ).toBe(1);
    });

    it("rounds the updated score to the scorer's four-decimal precision", () => {
        expect(
            recalculatePopularityForInstagramFollowers({
                popularity: 0.1234,
                previousInstagramFollowers: null,
                nextInstagramFollowers: 26_870,
                tiktokFollowers: null,
                youtubeFollowers: null,
            }),
        ).toBe(0.1245);
    });
});
