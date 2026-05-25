import { describe, expect, it } from "vitest";
import { selectChainFlagships } from "./findClubsWithCount";

describe("selectChainFlagships", () => {
    it("picks the location with the most upcoming shows per chain", () => {
        const { flagshipIds, locationCountByFlagship } = selectChainFlagships([
            { id: 1, chainId: 10, name: "Brea Improv", upcomingShows: 5 },
            { id: 2, chainId: 10, name: "Addison Improv", upcomingShows: 12 },
            { id: 3, chainId: 10, name: "Chicago Improv", upcomingShows: 8 },
            { id: 4, chainId: 20, name: "Funny Bone A", upcomingShows: 3 },
        ]);

        expect(flagshipIds.sort((a, b) => a - b)).toEqual([2, 4]);
        expect(locationCountByFlagship.get(2)).toBe(3);
        expect(locationCountByFlagship.get(4)).toBe(1);
    });

    it("breaks ties alphabetically by name", () => {
        const { flagshipIds } = selectChainFlagships([
            { id: 1, chainId: 10, name: "Zeta Club", upcomingShows: 7 },
            { id: 2, chainId: 10, name: "Alpha Club", upcomingShows: 7 },
        ]);

        // Same show count → "Alpha Club" wins alphabetically.
        expect(flagshipIds).toEqual([2]);
    });

    it("ignores clubs without a chain id", () => {
        const { flagshipIds, locationCountByFlagship } = selectChainFlagships([
            { id: 1, chainId: null, name: "Standalone", upcomingShows: 99 },
            { id: 2, chainId: 30, name: "Chain Only", upcomingShows: 1 },
        ]);

        expect(flagshipIds).toEqual([2]);
        expect(locationCountByFlagship.has(1)).toBe(false);
    });

    it("returns empty results for no chained clubs", () => {
        const { flagshipIds, locationCountByFlagship } = selectChainFlagships(
            [],
        );
        expect(flagshipIds).toEqual([]);
        expect(locationCountByFlagship.size).toBe(0);
    });
});
