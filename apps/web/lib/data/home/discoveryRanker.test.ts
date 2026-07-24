import { describe, expect, it } from "vitest";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";
import {
    isNearYouExplorationActor,
    rankNearYouCandidates,
    resolveNearYouDiscoveryPolicy,
    type NearYouFeatureSnapshot,
    type NearYouRankingCandidate,
} from "./discoveryRanker";

const NOW = new Date("2026-07-24T12:00:00.000Z");

function show(id: number, overrides: Partial<ShowDTO> = {}): ShowDTO {
    return {
        id,
        clubId: id,
        name: `Show ${id}`,
        date: new Date(NOW.getTime() + 7 * 24 * 60 * 60 * 1000),
        imageUrl: "",
        distanceMiles: 5,
        soldOut: false,
        ...overrides,
    };
}

function snapshot(
    overrides: Partial<NearYouFeatureSnapshot> = {},
): NearYouFeatureSnapshot {
    return {
        featureVersion: DISCOVERY_FEATURE_VERSION,
        asOf: NOW,
        prominence: 0.5,
        momentum: 0.5,
        growth: 0.5,
        confidence: 1,
        availability: "available",
        ...overrides,
    };
}

function candidate(
    id: number,
    featureOverrides: Partial<NearYouFeatureSnapshot> = {},
    showOverrides: Partial<ShowDTO> = {},
    affinity = 0.5,
): NearYouRankingCandidate {
    return {
        show: show(id, showOverrides),
        snapshot: snapshot(featureOverrides),
        affinity,
    };
}

function rankingContext(actorKey = "ordinary-actor", take = 8) {
    return {
        now: NOW,
        maxDistanceMiles: 25,
        actorKey,
        take,
    };
}

function findActor(predicate: (actorKey: string) => boolean): string {
    for (let index = 0; index < 10_000; index += 1) {
        const actorKey = `actor-${index}`;
        if (predicate(actorKey)) return actorKey;
    }
    throw new Error("Unable to find deterministic test actor");
}

describe("Near You experiment assignment", () => {
    it("is stable for the same actor and uses both experiment variants", () => {
        const candidateActor = findActor(
            (actorKey) =>
                resolveNearYouDiscoveryPolicy({
                    enabled: true,
                    actorKey,
                }).experimentVariant === "candidate",
        );
        const controlActor = findActor(
            (actorKey) =>
                resolveNearYouDiscoveryPolicy({
                    enabled: true,
                    actorKey,
                }).experimentVariant === "control",
        );

        expect(
            resolveNearYouDiscoveryPolicy({
                enabled: true,
                actorKey: candidateActor,
            }),
        ).toEqual(
            resolveNearYouDiscoveryPolicy({
                enabled: true,
                actorKey: candidateActor,
            }),
        );
        expect(
            resolveNearYouDiscoveryPolicy({
                enabled: true,
                actorKey: controlActor,
            }).experimentVariant,
        ).toBe("control");
    });

    it("immediately falls back to control when disabled or identity is absent", () => {
        expect(
            resolveNearYouDiscoveryPolicy({
                enabled: false,
                actorKey: "candidate-looking-actor",
            }),
        ).toEqual({
            experimentVariant: "control",
            policyVersion: "near-you-control-v1",
        });
        expect(
            resolveNearYouDiscoveryPolicy({
                enabled: true,
                actorKey: null,
            }).experimentVariant,
        ).toBe("control");
    });
});

describe("Near You candidate ranking", () => {
    it("excludes sold-out, past, out-of-radius, and snapshot-unavailable inventory", () => {
        const ranked = rankNearYouCandidates(
            [
                candidate(1),
                candidate(2, {}, { soldOut: true }),
                candidate(3, {}, { date: new Date(NOW.getTime() - 1) }),
                candidate(4, {}, { distanceMiles: 26 }),
                candidate(5, { availability: "unavailable" }),
            ],
            rankingContext("ordinary-actor"),
        );

        expect(ranked.map(({ id }) => id)).toEqual([1]);
    });

    it("allows confident local growth to outrank prominence", () => {
        const ranked = rankNearYouCandidates(
            [
                candidate(1, {
                    prominence: 1,
                    momentum: 0.2,
                    growth: 0.1,
                    confidence: 1,
                }),
                candidate(2, {
                    prominence: 0.1,
                    momentum: 0.9,
                    growth: 1,
                    confidence: 1,
                }),
            ],
            rankingContext("ordinary-actor", 2),
        );

        expect(ranked.map(({ id }) => id)).toEqual([2, 1]);
    });

    it("still respects geography, date, affinity, and confidence around growth", () => {
        const ranked = rankNearYouCandidates(
            [
                candidate(
                    1,
                    { growth: 1, momentum: 1, confidence: 0.05 },
                    {
                        distanceMiles: 24,
                        date: new Date(
                            NOW.getTime() + 29 * 24 * 60 * 60 * 1000,
                        ),
                    },
                    0,
                ),
                candidate(
                    2,
                    { growth: 0.55, momentum: 0.55, confidence: 1 },
                    {
                        distanceMiles: 2,
                        date: new Date(NOW.getTime() + 2 * 24 * 60 * 60 * 1000),
                    },
                    1,
                ),
            ],
            rankingContext("ordinary-actor", 2),
        );

        expect(ranked.map(({ id }) => id)).toEqual([2, 1]);
    });

    it("treats missing, future, and wrong-version snapshots as neutral low-confidence inputs", () => {
        const missing: NearYouRankingCandidate = {
            show: show(2),
            snapshot: null,
        };
        const wrongVersion: NearYouRankingCandidate = {
            show: show(3),
            snapshot: snapshot({
                featureVersion: "show-features-v0",
                prominence: 1,
                momentum: 1,
                growth: 1,
            }),
        };
        const futureSnapshot: NearYouRankingCandidate = {
            show: show(4),
            snapshot: snapshot({
                asOf: new Date(NOW.getTime() + 1),
                prominence: 1,
                momentum: 1,
                growth: 1,
            }),
        };
        const ranked = rankNearYouCandidates(
            [
                candidate(1, {
                    prominence: 0.6,
                    momentum: 0.6,
                    growth: 0.6,
                    confidence: 1,
                }),
                missing,
                wrongVersion,
                futureSnapshot,
            ],
            rankingContext("ordinary-actor", 4),
        );

        expect(ranked.map(({ id }) => id)).toEqual([1, 2, 3, 4]);
    });

    it("keeps unknown-inventory cold starts eligible", () => {
        const ranked = rankNearYouCandidates(
            [
                {
                    show: show(1),
                    snapshot: null,
                },
                candidate(2, { availability: "unknown", confidence: 0.2 }),
            ],
            rankingContext("ordinary-actor", 2),
        );

        expect(ranked.map(({ id }) => id).sort()).toEqual([1, 2]);
    });

    it("uses date then show id as deterministic tie breakers", () => {
        const sharedDate = new Date(NOW.getTime() + 3 * 24 * 60 * 60 * 1000);
        const ranked = rankNearYouCandidates(
            [
                candidate(3, {}, { date: sharedDate }),
                candidate(2, {}, { date: sharedDate }),
                candidate(1, {}, { date: new Date(sharedDate.getTime() - 1) }),
            ],
            rankingContext("ordinary-actor", 3),
        );

        expect(ranked.map(({ id }) => id)).toEqual([1, 2, 3]);
    });

    it("reserves one stable slot for a lower-prominence item in the exploration allocation", () => {
        const explorationActor = findActor(isNearYouExplorationActor);
        const inputs = Array.from({ length: 10 }, (_, index) =>
            candidate(index + 1, {
                prominence: index < 8 ? 0.9 : 0.05,
                momentum: index < 8 ? 0.8 : 0.1,
                growth: index < 8 ? 0.8 : 0.1,
            }),
        );

        const first = rankNearYouCandidates(
            inputs,
            rankingContext(explorationActor),
        );
        const second = rankNearYouCandidates(
            inputs,
            rankingContext(explorationActor),
        );

        expect(first).toEqual(second);
        expect(first).toHaveLength(8);
        expect(first.some(({ id }) => id > 8)).toBe(true);
    });
});
