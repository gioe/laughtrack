import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";

const DAY_MS = 24 * 60 * 60 * 1000;
const MIN_BEHAVIOR_ACTORS = 20;
const MIN_FAVORITE_EVENTS = 5;
const MIN_SOCIAL_SERIES = 3;

export const DISCOVERY_FEATURE_VERSION = "show-features-v1";
export const DISCOVERY_RECENT_DAYS = 7;
export const DISCOVERY_BASELINE_DAYS = 28;

export type DiscoveryAvailability = "available" | "unknown" | "unavailable";

export interface DiscoveryActivityObservation {
    actorKey: string;
    observedAt: Date;
}

export interface DiscoveryFollowerObservation {
    comedianId: number;
    platform: string;
    followerCount: number;
    observedAt: Date;
}

export interface DiscoveryFeatureInput {
    showId: number;
    asOf: Date;
    legacyPopularity: number | null;
    showDate: Date;
    ticketsSoldOut: boolean;
    hasPurchasePath: boolean;
    followerObservations: readonly DiscoveryFollowerObservation[];
    favoriteCreatedAt: readonly Date[];
    impressions: readonly DiscoveryActivityObservation[];
    detailEngagements: readonly DiscoveryActivityObservation[];
    ticketIntents: readonly DiscoveryActivityObservation[];
    discoveryCoverageStart?: Date;
    favoriteCoverageStart?: Date;
}

export interface DiscoveryFeatureWindows {
    baselineStart: Date;
    recentStart: Date;
    trailing28Start: Date;
    socialBaselineStart: Date;
    end: Date;
}

interface GrowthComponent {
    name: "behavior" | "favorites" | "social";
    signedValue: number;
    confidence: number;
    weight: number;
}

export interface DiscoveryFeatureEvidence {
    windows: {
        baselineStart: string;
        recentStart: string;
        trailing28Start: string;
        socialBaselineStart: string;
        end: string;
    };
    behavior: {
        momentumWindow: "recent" | "trailing28" | "insufficient";
        recentImpressionActors: number;
        baselineImpressionActors: number;
        trailing28ImpressionActors: number;
        recentDetailActors: number;
        baselineDetailActors: number;
        recentTicketIntentActors: number;
        baselineTicketIntentActors: number;
        recentDemandActors: number;
        baselineDemandActors: number;
        recentDemandRate: number | null;
        baselineDemandRate: number | null;
        growth: number | null;
        confidence: number;
    };
    favorites: {
        recentCount: number;
        baselineCount: number;
        recentDailyRate: number;
        baselineDailyRate: number;
        growth: number | null;
        confidence: number;
    };
    social: {
        pairedSeries: number;
        observedSeries: number;
        growth: number | null;
        confidence: number;
    };
    confidenceReasons: string[];
}

export interface DiscoveryFeatureSnapshot {
    showId: number;
    featureVersion: string;
    asOf: Date;
    prominence: number;
    momentum: number;
    growth: number;
    confidence: number;
    availability: DiscoveryAvailability;
    evidence: DiscoveryFeatureEvidence;
}

function clamp(value: number, minimum: number, maximum: number): number {
    return Math.min(Math.max(value, minimum), maximum);
}

function round(value: number): number {
    return Number(value.toFixed(6));
}

function startOfUtcDay(value: Date): Date {
    return new Date(
        Date.UTC(
            value.getUTCFullYear(),
            value.getUTCMonth(),
            value.getUTCDate(),
        ),
    );
}

function isValidDate(value: Date): boolean {
    return !Number.isNaN(value.getTime());
}

function isWithin(value: Date, start: Date, end: Date): boolean {
    const timestamp = value.getTime();
    return timestamp >= start.getTime() && timestamp < end.getTime();
}

function uniqueActors(
    observations: readonly DiscoveryActivityObservation[],
    start: Date,
    end: Date,
): Set<string> {
    return new Set(
        observations
            .filter(
                (observation) =>
                    observation.actorKey.length > 0 &&
                    isValidDate(observation.observedAt) &&
                    isWithin(observation.observedAt, start, end),
            )
            .map((observation) => observation.actorKey),
    );
}

function demandActors(
    observations: readonly DiscoveryActivityObservation[],
    exposedActors: ReadonlySet<string>,
    start: Date,
    end: Date,
): Set<string> {
    const actors = uniqueActors(observations, start, end);

    return new Set([...actors].filter((actor) => exposedActors.has(actor)));
}

function normalizedChange(recent: number, baseline: number): number {
    if (recent === baseline) return 0;
    const denominator = Math.max(Math.abs(recent), Math.abs(baseline), 0.05);
    return clamp((recent - baseline) / denominator, -1, 1);
}

function coverageIncludes(
    coverageStart: Date | undefined,
    requiredStart: Date,
): boolean {
    return Boolean(
        coverageStart &&
            isValidDate(coverageStart) &&
            coverageStart.getTime() <= requiredStart.getTime(),
    );
}

export function getDiscoveryFeatureWindows(
    asOf: Date,
): DiscoveryFeatureWindows {
    if (!isValidDate(asOf)) {
        throw new RangeError("asOf must be a valid date");
    }

    const end = startOfUtcDay(asOf);
    const recentStart = new Date(
        end.getTime() - DISCOVERY_RECENT_DAYS * DAY_MS,
    );
    const baselineStart = new Date(
        recentStart.getTime() - DISCOVERY_BASELINE_DAYS * DAY_MS,
    );
    const trailing28Start = new Date(
        end.getTime() - DISCOVERY_BASELINE_DAYS * DAY_MS,
    );
    const socialBaselineStart = new Date(
        trailing28Start.getTime() - DISCOVERY_BASELINE_DAYS * DAY_MS,
    );

    return {
        baselineStart,
        recentStart,
        trailing28Start,
        socialBaselineStart,
        end,
    };
}

function getAvailability(input: DiscoveryFeatureInput): DiscoveryAvailability {
    if (
        input.showDate.getTime() <= input.asOf.getTime() ||
        input.ticketsSoldOut
    ) {
        return "unavailable";
    }
    return input.hasPurchasePath ? "available" : "unknown";
}

function computeBehavior(
    input: DiscoveryFeatureInput,
    windows: DiscoveryFeatureWindows,
    reasons: Set<string>,
): {
    momentum: number;
    component: GrowthComponent | null;
    evidence: DiscoveryFeatureEvidence["behavior"];
} {
    const recentImpressions = uniqueActors(
        input.impressions,
        windows.recentStart,
        windows.end,
    );
    const baselineImpressions = uniqueActors(
        input.impressions,
        windows.baselineStart,
        windows.recentStart,
    );
    const trailing28Impressions = uniqueActors(
        input.impressions,
        windows.trailing28Start,
        windows.end,
    );
    const recentDetails = demandActors(
        input.detailEngagements,
        recentImpressions,
        windows.recentStart,
        windows.end,
    );
    const baselineDetails = demandActors(
        input.detailEngagements,
        baselineImpressions,
        windows.baselineStart,
        windows.recentStart,
    );
    const recentTickets = demandActors(
        input.ticketIntents,
        recentImpressions,
        windows.recentStart,
        windows.end,
    );
    const baselineTickets = demandActors(
        input.ticketIntents,
        baselineImpressions,
        windows.baselineStart,
        windows.recentStart,
    );
    const trailing28Details = demandActors(
        input.detailEngagements,
        trailing28Impressions,
        windows.trailing28Start,
        windows.end,
    );
    const trailing28Tickets = demandActors(
        input.ticketIntents,
        trailing28Impressions,
        windows.trailing28Start,
        windows.end,
    );
    const recentDemand = new Set([...recentDetails, ...recentTickets]);
    const baselineDemand = new Set([...baselineDetails, ...baselineTickets]);
    const trailing28Demand = new Set([
        ...trailing28Details,
        ...trailing28Tickets,
    ]);

    const recentRate =
        recentImpressions.size > 0
            ? recentDemand.size / recentImpressions.size
            : null;
    const baselineRate =
        baselineImpressions.size > 0
            ? baselineDemand.size / baselineImpressions.size
            : null;

    let momentum = 0;
    let momentumWindow: "recent" | "trailing28" | "insufficient" =
        "insufficient";
    let confidence = 0;

    if (recentImpressions.size >= MIN_BEHAVIOR_ACTORS) {
        momentum = recentRate ?? 0;
        momentumWindow = "recent";
        confidence = clamp(
            recentImpressions.size / (MIN_BEHAVIOR_ACTORS * 2),
            0,
            1,
        );
    } else if (trailing28Impressions.size >= MIN_BEHAVIOR_ACTORS) {
        momentum = trailing28Demand.size / trailing28Impressions.size;
        momentumWindow = "trailing28";
        confidence =
            0.75 *
            clamp(trailing28Impressions.size / (MIN_BEHAVIOR_ACTORS * 2), 0, 1);
        reasons.add("sparse_recent_impressions");
    } else {
        reasons.add("insufficient_impressions");
    }

    const hasGrowthCoverage = coverageIncludes(
        input.discoveryCoverageStart,
        windows.baselineStart,
    );
    const hasGrowthEvidence =
        hasGrowthCoverage &&
        recentImpressions.size >= MIN_BEHAVIOR_ACTORS &&
        baselineImpressions.size >= MIN_BEHAVIOR_ACTORS &&
        recentRate !== null &&
        baselineRate !== null;
    const signedGrowth = hasGrowthEvidence
        ? normalizedChange(recentRate, baselineRate)
        : null;

    if (!hasGrowthCoverage) reasons.add("incomplete_attribution_history");
    else if (!hasGrowthEvidence) reasons.add("missing_behavior_baseline");

    return {
        momentum: round(clamp(momentum, 0, 1)),
        component:
            signedGrowth === null
                ? null
                : {
                      name: "behavior",
                      signedValue: signedGrowth,
                      confidence: Math.min(
                          1,
                          recentImpressions.size / MIN_BEHAVIOR_ACTORS,
                          baselineImpressions.size / MIN_BEHAVIOR_ACTORS,
                      ),
                      weight: 0.5,
                  },
        evidence: {
            momentumWindow,
            recentImpressionActors: recentImpressions.size,
            baselineImpressionActors: baselineImpressions.size,
            trailing28ImpressionActors: trailing28Impressions.size,
            recentDetailActors: recentDetails.size,
            baselineDetailActors: baselineDetails.size,
            recentTicketIntentActors: recentTickets.size,
            baselineTicketIntentActors: baselineTickets.size,
            recentDemandActors: recentDemand.size,
            baselineDemandActors: baselineDemand.size,
            recentDemandRate: recentRate === null ? null : round(recentRate),
            baselineDemandRate:
                baselineRate === null ? null : round(baselineRate),
            growth: signedGrowth === null ? null : round(signedGrowth),
            confidence: round(confidence),
        },
    };
}

function computeFavorites(
    input: DiscoveryFeatureInput,
    windows: DiscoveryFeatureWindows,
    reasons: Set<string>,
): {
    component: GrowthComponent | null;
    evidence: DiscoveryFeatureEvidence["favorites"];
} {
    const validDates = input.favoriteCreatedAt.filter(isValidDate);
    const recentCount = validDates.filter((date) =>
        isWithin(date, windows.recentStart, windows.end),
    ).length;
    const baselineCount = validDates.filter((date) =>
        isWithin(date, windows.baselineStart, windows.recentStart),
    ).length;
    const recentDailyRate = recentCount / DISCOVERY_RECENT_DAYS;
    const baselineDailyRate = baselineCount / DISCOVERY_BASELINE_DAYS;
    const hasCoverage = coverageIncludes(
        input.favoriteCoverageStart,
        windows.baselineStart,
    );
    const eventCount = recentCount + baselineCount;
    const confidence = hasCoverage
        ? clamp(eventCount / MIN_FAVORITE_EVENTS, 0, 1)
        : 0;
    const signedGrowth = hasCoverage
        ? normalizedChange(recentDailyRate, baselineDailyRate)
        : null;

    if (!hasCoverage) reasons.add("missing_favorite_baseline");

    return {
        component:
            signedGrowth === null
                ? null
                : {
                      name: "favorites",
                      signedValue: signedGrowth,
                      confidence,
                      weight: 0.25,
                  },
        evidence: {
            recentCount,
            baselineCount,
            recentDailyRate: round(recentDailyRate),
            baselineDailyRate: round(baselineDailyRate),
            growth: signedGrowth === null ? null : round(signedGrowth),
            confidence: round(confidence),
        },
    };
}

function latestObservation(
    observations: readonly DiscoveryFollowerObservation[],
    start: Date,
    end: Date,
): DiscoveryFollowerObservation | null {
    return (
        observations
            .filter(
                (observation) =>
                    Number.isInteger(observation.followerCount) &&
                    observation.followerCount >= 0 &&
                    isValidDate(observation.observedAt) &&
                    isWithin(observation.observedAt, start, end),
            )
            .sort(
                (a, b) => b.observedAt.getTime() - a.observedAt.getTime(),
            )[0] ?? null
    );
}

function computeSocial(
    input: DiscoveryFeatureInput,
    windows: DiscoveryFeatureWindows,
    reasons: Set<string>,
): {
    component: GrowthComponent | null;
    evidence: DiscoveryFeatureEvidence["social"];
} {
    const series = new Map<string, DiscoveryFollowerObservation[]>();
    for (const observation of input.followerObservations) {
        const key = `${observation.comedianId}:${observation.platform}`;
        const values = series.get(key) ?? [];
        values.push(observation);
        series.set(key, values);
    }

    const changes: number[] = [];
    for (const observations of series.values()) {
        const recent = latestObservation(
            observations,
            windows.trailing28Start,
            windows.end,
        );
        const baseline = latestObservation(
            observations,
            windows.socialBaselineStart,
            windows.trailing28Start,
        );
        if (!recent || !baseline) continue;

        const recentLog = Math.log1p(recent.followerCount);
        const baselineLog = Math.log1p(baseline.followerCount);
        changes.push(clamp((recentLog - baselineLog) / Math.log(2), -1, 1));
    }

    const observedSeries = series.size;
    const pairedSeries = changes.length;
    const confidence =
        observedSeries === 0
            ? 0
            : clamp(
                  pairedSeries / Math.max(observedSeries, MIN_SOCIAL_SERIES),
                  0,
                  1,
              );
    const signedGrowth =
        pairedSeries === 0
            ? null
            : changes.reduce((sum, value) => sum + value, 0) / pairedSeries;

    if (pairedSeries === 0) reasons.add("missing_social_baseline");

    return {
        component:
            signedGrowth === null
                ? null
                : {
                      name: "social",
                      signedValue: signedGrowth,
                      confidence,
                      weight: 0.25,
                  },
        evidence: {
            pairedSeries,
            observedSeries,
            growth: signedGrowth === null ? null : round(signedGrowth),
            confidence: round(confidence),
        },
    };
}

export function computeDiscoveryFeatures(
    input: DiscoveryFeatureInput,
): DiscoveryFeatureSnapshot {
    if (!Number.isInteger(input.showId) || input.showId <= 0) {
        throw new RangeError("showId must be a positive integer");
    }
    if (!isValidDate(input.asOf) || !isValidDate(input.showDate)) {
        throw new RangeError("asOf and showDate must be valid dates");
    }

    const windows = getDiscoveryFeatureWindows(input.asOf);
    const reasons = new Set<string>();
    const behavior = computeBehavior(input, windows, reasons);
    const favorites = computeFavorites(input, windows, reasons);
    const social = computeSocial(input, windows, reasons);
    const availability = getAvailability(input);
    if (availability === "unknown") reasons.add("unknown_inventory");

    const components = [
        behavior.component,
        favorites.component,
        social.component,
    ].filter(
        (component): component is GrowthComponent =>
            component !== null && component.confidence > 0,
    );
    const totalWeight = components.reduce(
        (sum, component) => sum + component.weight,
        0,
    );
    const signedGrowth =
        totalWeight === 0
            ? 0
            : components.reduce(
                  (sum, component) =>
                      sum +
                      component.signedValue *
                          component.weight *
                          component.confidence,
                  0,
              ) / totalWeight;
    const growth = 0.5 + signedGrowth / 2;

    const signalConfidence =
        (behavior.evidence.confidence +
            favorites.evidence.confidence +
            social.evidence.confidence) /
        3;
    const availabilityConfidence = availability === "unknown" ? 0.5 : 1;
    const confidence = signalConfidence * 0.8 + availabilityConfidence * 0.2;

    return {
        showId: input.showId,
        featureVersion: DISCOVERY_FEATURE_VERSION,
        asOf: new Date(input.asOf),
        prominence: round(
            clamp(
                Number.isFinite(input.legacyPopularity ?? Number.NaN)
                    ? (input.legacyPopularity as number)
                    : 0,
                0,
                1,
            ),
        ),
        momentum: behavior.momentum,
        growth: round(clamp(growth, 0, 1)),
        confidence: round(clamp(confidence, 0, 1)),
        availability,
        evidence: {
            windows: {
                baselineStart: windows.baselineStart.toISOString(),
                recentStart: windows.recentStart.toISOString(),
                trailing28Start: windows.trailing28Start.toISOString(),
                socialBaselineStart: windows.socialBaselineStart.toISOString(),
                end: windows.end.toISOString(),
            },
            behavior: behavior.evidence,
            favorites: favorites.evidence,
            social: social.evidence,
            confidenceReasons: [...reasons].sort(),
        },
    };
}

export function buildDiscoveryFeatureSnapshotUpsert(
    snapshot: DiscoveryFeatureSnapshot,
): Prisma.Sql {
    return Prisma.sql`
        INSERT INTO discovery_show_feature_snapshots (
            show_id,
            feature_version,
            as_of,
            prominence,
            momentum,
            growth,
            confidence,
            availability,
            evidence
        )
        VALUES (
            ${snapshot.showId},
            ${snapshot.featureVersion},
            ${snapshot.asOf},
            ${snapshot.prominence},
            ${snapshot.momentum},
            ${snapshot.growth},
            ${snapshot.confidence},
            ${snapshot.availability},
            CAST(${JSON.stringify(snapshot.evidence)} AS JSONB)
        )
        ON CONFLICT (show_id, feature_version, as_of)
        DO UPDATE SET
            prominence = EXCLUDED.prominence,
            momentum = EXCLUDED.momentum,
            growth = EXCLUDED.growth,
            confidence = EXCLUDED.confidence,
            availability = EXCLUDED.availability,
            evidence = EXCLUDED.evidence
    `;
}

export async function recomputeDiscoveryFeatureSnapshots(
    inputs: readonly DiscoveryFeatureInput[],
): Promise<DiscoveryFeatureSnapshot[]> {
    const snapshots = inputs.map(computeDiscoveryFeatures);
    await db.$transaction(
        snapshots.map((snapshot) =>
            db.$executeRaw(buildDiscoveryFeatureSnapshotUpsert(snapshot)),
        ),
    );
    return snapshots;
}
