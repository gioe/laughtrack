import { describe, expect, it } from "vitest";

import {
    CLUB_DISCOVERY_PROFILE_CLASSIFIED_THRESHOLD,
    buildClubDiscoveryProfile,
} from "./clubDiscoveryProfiles";

const BASE_TIME = new Date("2026-06-29T12:00:00.000Z");

function showTypeRows(showTypes: string[]) {
    return showTypes.map((showType, index) => ({
        id: index + 1,
        showType,
    }));
}

describe("buildClubDiscoveryProfile", () => {
    it("marks a dominant show type as primary when it reaches the 60 percent classified threshold", () => {
        const profile = buildClubDiscoveryProfile({
            clubId: 42,
            rows: showTypeRows([
                "standup",
                "standup",
                "standup",
                "improv",
                "unknown",
            ]),
            computedAt: BASE_TIME,
        });

        expect(CLUB_DISCOVERY_PROFILE_CLASSIFIED_THRESHOLD).toBe(0.6);
        expect(profile).toEqual({
            clubId: 42,
            primaryShowType: "standup",
            showTypeCounts: { improv: 1, standup: 3, unknown: 1 },
            comedyShowCount: 4,
            nonComedyShowCount: 0,
            mixedProgramming: false,
            confidence: 0.6,
            computedAt: BASE_TIME,
        });
    });

    it("marks mixed programming when no classified show type reaches the threshold", () => {
        const profile = buildClubDiscoveryProfile({
            clubId: 7,
            rows: showTypeRows(["standup", "standup", "improv", "music"]),
            computedAt: BASE_TIME,
        });

        expect(profile.primaryShowType).toBeNull();
        expect(profile.showTypeCounts).toEqual({
            improv: 1,
            music: 1,
            standup: 2,
        });
        expect(profile.comedyShowCount).toBe(3);
        expect(profile.nonComedyShowCount).toBe(1);
        expect(profile.mixedProgramming).toBe(true);
        expect(profile.confidence).toBe(0.5);
    });

    it("keeps unknown-heavy windows unknown while still counting classified comedy inventory", () => {
        const profile = buildClubDiscoveryProfile({
            clubId: 8,
            rows: showTypeRows(["unknown", "unknown", "unknown", "standup"]),
            computedAt: BASE_TIME,
        });

        expect(profile.primaryShowType).toBe("standup");
        expect(profile.showTypeCounts).toEqual({ standup: 1, unknown: 3 });
        expect(profile.comedyShowCount).toBe(1);
        expect(profile.nonComedyShowCount).toBe(0);
        expect(profile.mixedProgramming).toBe(false);
        expect(profile.confidence).toBe(0.25);
    });

    it("returns an unknown low-confidence profile for an empty discovery window", () => {
        const profile = buildClubDiscoveryProfile({
            clubId: 9,
            rows: [],
            computedAt: BASE_TIME,
        });

        expect(profile).toEqual({
            clubId: 9,
            primaryShowType: "unknown",
            showTypeCounts: {},
            comedyShowCount: 0,
            nonComedyShowCount: 0,
            mixedProgramming: false,
            confidence: 0,
            computedAt: BASE_TIME,
        });
    });
});
