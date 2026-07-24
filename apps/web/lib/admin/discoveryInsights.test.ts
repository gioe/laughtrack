import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));

import {
    buildDiscoveryEvaluation,
    getDiscoveryEvaluation,
} from "./discoveryInsights";
import { db } from "@/lib/db";

const NOW = new Date("2026-07-24T12:00:00.000Z");
const mockQueryRaw = vi.mocked(db.$queryRaw);

function outcome(
    overrides: Record<string, unknown> = {},
): Record<string, unknown> {
    return {
        experimentVariant: "control",
        policyVersion: "near-you-control-v1",
        assignmentBucket: "eligible",
        impressionActors: 1_200,
        impressions: 4_800,
        distinctShows: 80,
        detailActors: 360,
        detailEngagedShows: 40,
        ticketIntentActors: 65,
        actionableTicketIntentActors: 60,
        soldOutDemandActors: 3,
        unknownAvailabilityTicketIntentActors: 2,
        actionableImpressions: 4_320,
        unavailableImpressions: 20,
        knownGeoImpressions: 4_600,
        geographicallyEligibleImpressions: 4_600,
        newcomerImpressions: 720,
        explorationImpressions: 0,
        explorationActors: 0,
        explorationDetailActors: 0,
        explorationTicketIntentActors: 0,
        missingFeatureImpressions: 4_800,
        latestImpressedAt: new Date("2026-07-24T11:00:00.000Z"),
        latestRecordedAt: new Date("2026-07-24T11:00:01.000Z"),
        ...overrides,
    };
}

function feature(
    period: "current" | "baseline",
    overrides: Record<string, unknown> = {},
): Record<string, unknown> {
    const current = period === "current";
    return {
        period,
        snapshots: 100,
        prominenceMean: current ? 0.52 : 0.5,
        prominenceP10: 0.1,
        prominenceP50: 0.5,
        prominenceP90: 0.9,
        momentumMean: current ? 0.51 : 0.5,
        momentumP10: 0.1,
        momentumP50: 0.5,
        momentumP90: 0.9,
        growthMean: current ? 0.53 : 0.5,
        growthP10: 0.1,
        growthP50: 0.5,
        growthP90: 0.9,
        confidenceMean: current ? 0.62 : 0.6,
        confidenceP10: 0.2,
        confidenceP50: 0.6,
        confidenceP90: 0.9,
        availableSnapshots: 80,
        unknownSnapshots: 15,
        unavailableSnapshots: 5,
        staleSnapshots: 0,
        latestAsOf: current
            ? new Date("2026-07-24T08:00:00.000Z")
            : new Date("2026-07-10T08:00:00.000Z"),
        latestComputedAt: current
            ? new Date("2026-07-24T08:05:00.000Z")
            : new Date("2026-07-10T08:05:00.000Z"),
        ...overrides,
    };
}

function build(
    outcomes: Record<string, unknown>[],
    concentrations: Record<string, unknown>[] = [],
    features: Record<string, unknown>[] = [
        feature("current"),
        feature("baseline"),
    ],
) {
    return buildDiscoveryEvaluation(
        { days: 14, now: NOW },
        outcomes as never,
        concentrations as never,
        features as never,
    );
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("discovery experiment evaluation", () => {
    it("compares the impression-normalized primary metric and guardrails by eligible variant", async () => {
        const outcomes = [
            outcome(),
            outcome({
                experimentVariant: "candidate",
                policyVersion: "near-you-candidate-v1",
                actionableTicketIntentActors: 72,
                ticketIntentActors: 78,
                detailActors: 384,
                actionableImpressions: 4_416,
                explorationImpressions: 20,
                explorationActors: 10,
                explorationDetailActors: 4,
                explorationTicketIntentActors: 2,
                missingFeatureImpressions: 0,
            }),
            outcome({
                assignmentBucket: "bootstrap",
                impressionActors: 30,
                impressions: 100,
            }),
            outcome({
                assignmentBucket: "legacy_unknown",
                impressionActors: 12,
                impressions: 40,
            }),
        ];
        mockQueryRaw
            .mockResolvedValueOnce(outcomes as never)
            .mockResolvedValueOnce([
                {
                    experimentVariant: "control",
                    policyVersion: "near-you-control-v1",
                    entityId: 1,
                    impressions: 400,
                },
                {
                    experimentVariant: "control",
                    policyVersion: "near-you-control-v1",
                    entityId: 2,
                    impressions: 400,
                },
                {
                    experimentVariant: "candidate",
                    policyVersion: "near-you-candidate-v1",
                    entityId: 1,
                    impressions: 200,
                },
                {
                    experimentVariant: "candidate",
                    policyVersion: "near-you-candidate-v1",
                    entityId: 2,
                    impressions: 600,
                },
            ] as never)
            .mockResolvedValueOnce([
                feature("current"),
                feature("baseline"),
            ] as never);

        const report = await getDiscoveryEvaluation({ days: 14, now: NOW });
        const control = report.variants.find(
            ({ experimentVariant }) => experimentVariant === "control",
        );
        const candidate = report.variants.find(
            ({ experimentVariant }) => experimentVariant === "candidate",
        );

        expect(mockQueryRaw).toHaveBeenCalledTimes(3);
        expect(control?.primary.actionableTicketIntent.rate).toBe(0.05);
        expect(candidate?.primary.actionableTicketIntent.rate).toBe(0.06);
        expect(candidate?.guardrails.showDetail.rate).toBe(0.32);
        expect(candidate?.guardrails.actionableResultCoverageRate).toBe(0.92);
        expect(candidate?.guardrails.geographicEligibilityRate).toBeCloseTo(1);
        expect(candidate?.guardrails.newcomerExposureRate).toBe(0.15);
        expect(candidate?.exploration).toEqual({
            selectedImpressions: 20,
            exposedActors: 10,
            detailEngagementRate: 0.4,
            ticketIntentRate: 0.2,
        });
        expect(report.comparison.primaryRelativeDelta).toBeCloseTo(0.2);
        expect(report.traffic).toEqual({
            assignmentEligibleActors: 2_400,
            bootstrapControlActors: 30,
            legacyUnknownActors: 12,
        });
        expect(report.decision.status).toBe("ship");
    });

    it("surfaces feature drift, stale inputs, missing context, and ranking concentration", () => {
        const report = build(
            [
                outcome(),
                outcome({
                    experimentVariant: "candidate",
                    policyVersion: "near-you-candidate-v1",
                    missingFeatureImpressions: 1_200,
                }),
            ],
            [
                {
                    experimentVariant: "candidate",
                    policyVersion: "near-you-candidate-v1",
                    entityId: 1,
                    impressions: 700,
                },
                {
                    experimentVariant: "candidate",
                    policyVersion: "near-you-candidate-v1",
                    entityId: 2,
                    impressions: 100,
                },
            ],
            [
                feature("current", {
                    prominenceMean: 0.7,
                    staleSnapshots: 10,
                    latestComputedAt: new Date("2026-07-20T00:00:00.000Z"),
                }),
                feature("baseline", { prominenceMean: 0.5 }),
            ],
        );
        const candidate = report.variants.find(
            ({ experimentVariant }) => experimentVariant === "candidate",
        );

        expect(report.drift.stale).toBe(true);
        expect(report.drift.meanShifts.prominence).toBeCloseTo(0.2);
        expect(report.drift.shiftedFeatures).toContain("prominence");
        expect(candidate?.dataQuality.missingFeatureContextRate).toBe(0.25);
        expect(candidate?.rankingConcentration.topShowExposureShare).toBe(
            0.875,
        );
        expect(candidate?.rankingConcentration.exposureHhi).toBeCloseTo(
            0.78125,
        );
    });

    it("keeps sold-out demand separate from actionable ticket discovery", () => {
        const report = build([
            outcome({
                impressionActors: 200,
                ticketIntentActors: 40,
                actionableTicketIntentActors: 18,
                soldOutDemandActors: 15,
                unknownAvailabilityTicketIntentActors: 7,
            }),
        ]);
        const control = report.variants[0];

        expect(control.primary.allTicketIntent.rate).toBe(0.2);
        expect(control.primary.actionableTicketIntent.rate).toBe(0.09);
        expect(control.primary.soldOutDemand.rate).toBe(0.075);
        expect(control.primary.unknownAvailabilityTicketIntent.rate).toBe(
            0.035,
        );
    });

    it("does not dilute assignment-eligible control with bootstrap or legacy traffic", () => {
        const report = build([
            outcome({
                impressionActors: 100,
                actionableTicketIntentActors: 20,
            }),
            outcome({
                assignmentBucket: "bootstrap",
                impressionActors: 900,
                actionableTicketIntentActors: 0,
            }),
            outcome({
                assignmentBucket: "legacy_unknown",
                impressionActors: 500,
                actionableTicketIntentActors: 0,
            }),
        ]);

        expect(report.variants).toHaveLength(1);
        expect(report.variants[0].qualifiedImpressionActors).toBe(100);
        expect(report.variants[0].primary.actionableTicketIntent.rate).toBe(
            0.2,
        );
        expect(report.traffic.bootstrapControlActors).toBe(900);
        expect(report.traffic.legacyUnknownActors).toBe(500);
    });
});
