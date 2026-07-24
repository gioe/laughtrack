import { db } from "@/lib/db";
import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { Prisma } from "@prisma/client";

const DAY_MS = 24 * 60 * 60 * 1000;
const FEATURE_STALE_HOURS = 48;
const MINIMUM_ACTORS_PER_ARM = 1_000;
const MINIMUM_TICKET_INTENT_ACTORS_PER_ARM = 50;
const MINIMUM_OBSERVATION_DAYS = 14;

type Numeric = bigint | number;
type AssignmentBucket = "eligible" | "bootstrap" | "legacy_unknown";

interface OutcomeRow {
    experimentVariant: string;
    policyVersion: string;
    assignmentBucket: AssignmentBucket;
    impressionActors: Numeric;
    impressions: Numeric;
    distinctShows: Numeric;
    detailActors: Numeric;
    detailEngagedShows: Numeric;
    ticketIntentActors: Numeric;
    actionableTicketIntentActors: Numeric;
    soldOutDemandActors: Numeric;
    unknownAvailabilityTicketIntentActors: Numeric;
    actionableImpressions: Numeric;
    unavailableImpressions: Numeric;
    knownGeoImpressions: Numeric;
    geographicallyEligibleImpressions: Numeric;
    newcomerImpressions: Numeric;
    explorationImpressions: Numeric;
    explorationActors: Numeric;
    explorationDetailActors: Numeric;
    explorationTicketIntentActors: Numeric;
    missingFeatureImpressions: Numeric;
    latestImpressedAt: Date | string | null;
    latestRecordedAt: Date | string | null;
}

interface ConcentrationRow {
    experimentVariant: string;
    policyVersion: string;
    entityId: number;
    impressions: Numeric;
}

interface FeatureDistributionRow {
    period: "current" | "baseline";
    snapshots: Numeric;
    prominenceMean: number | null;
    prominenceP10: number | null;
    prominenceP50: number | null;
    prominenceP90: number | null;
    momentumMean: number | null;
    momentumP10: number | null;
    momentumP50: number | null;
    momentumP90: number | null;
    growthMean: number | null;
    growthP10: number | null;
    growthP50: number | null;
    growthP90: number | null;
    confidenceMean: number | null;
    confidenceP10: number | null;
    confidenceP50: number | null;
    confidenceP90: number | null;
    availableSnapshots: Numeric;
    unknownSnapshots: Numeric;
    unavailableSnapshots: Numeric;
    staleSnapshots: Numeric;
    latestAsOf: Date | string | null;
    latestComputedAt: Date | string | null;
}

export interface DiscoveryEvaluationOptions {
    days?: number;
    now?: Date;
}

interface RateMetric {
    actors: number;
    rate: number | null;
}

export interface DiscoveryVariantEvaluation {
    experimentVariant: string;
    policyVersion: string;
    qualifiedImpressionActors: number;
    impressions: number;
    distinctShows: number;
    primary: {
        actionableTicketIntent: RateMetric;
        allTicketIntent: RateMetric;
        soldOutDemand: RateMetric;
        unknownAvailabilityTicketIntent: RateMetric;
    };
    guardrails: {
        showDetail: RateMetric;
        engagedShowCoverageRate: number | null;
        actionableResultCoverageRate: number | null;
        geographicEligibilityRate: number | null;
        geographicMeasurementCoverageRate: number | null;
        newcomerExposureRate: number | null;
    };
    exploration: {
        selectedImpressions: number;
        exposedActors: number;
        detailEngagementRate: number | null;
        ticketIntentRate: number | null;
    };
    rankingConcentration: {
        topShowExposureShare: number | null;
        exposureHhi: number | null;
    };
    dataQuality: {
        missingFeatureContextRate: number | null;
        latestImpressedAt: string | null;
        latestRecordedAt: string | null;
    };
}

interface DistributionSummary {
    count: number;
    mean: number | null;
    p10: number | null;
    p50: number | null;
    p90: number | null;
}

interface FeaturePeriodSummary {
    snapshots: number;
    prominence: DistributionSummary;
    momentum: DistributionSummary;
    growth: DistributionSummary;
    confidence: DistributionSummary;
    availability: {
        available: number;
        unknown: number;
        unavailable: number;
    };
    staleSnapshots: number;
    latestAsOf: string | null;
    latestComputedAt: string | null;
}

export interface DiscoveryEvaluation {
    window: {
        start: string;
        end: string;
        days: number;
    };
    contract: {
        primaryMetric: "actionable_ticket_intent_actors_per_qualified_impression_actor";
        minimumActorsPerArm: number;
        minimumTicketIntentActorsPerArm: number;
        minimumObservationDays: number;
        featureVersion: string;
        featureStaleAfterHours: number;
    };
    traffic: {
        assignmentEligibleActors: number;
        bootstrapControlActors: number;
        legacyUnknownActors: number;
    };
    variants: DiscoveryVariantEvaluation[];
    comparison: {
        candidatePolicyVersion: string | null;
        controlPolicyVersion: string | null;
        primaryRelativeDelta: number | null;
        detailRelativeDelta: number | null;
        actionableCoverageDelta: number | null;
    };
    drift: {
        current: FeaturePeriodSummary | null;
        baseline: FeaturePeriodSummary | null;
        meanShifts: Record<
            "prominence" | "momentum" | "growth" | "confidence",
            number | null
        >;
        shiftedFeatures: string[];
        stale: boolean;
    };
    decision: {
        status: "insufficient" | "ship" | "tune" | "rollback";
        reasons: string[];
    };
}

function number(value: Numeric | null | undefined): number {
    return value === null || value === undefined ? 0 : Number(value);
}

function iso(value: Date | string | null): string | null {
    if (!value) return null;
    const parsed = value instanceof Date ? value : new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function rate(numerator: number, denominator: number): number | null {
    return denominator > 0 ? numerator / denominator : null;
}

function relativeDelta(
    candidate: number | null,
    control: number | null,
): number | null {
    if (candidate === null || control === null || control === 0) return null;
    return (candidate - control) / control;
}

function difference(
    candidate: number | null,
    control: number | null,
): number | null {
    if (candidate === null || control === null) return null;
    return candidate - control;
}

function concentration(
    rows: readonly ConcentrationRow[],
): DiscoveryVariantEvaluation["rankingConcentration"] {
    const exposures = rows.map((row) => number(row.impressions));
    const total = exposures.reduce((sum, value) => sum + value, 0);
    if (total === 0) {
        return { topShowExposureShare: null, exposureHhi: null };
    }
    const shares = exposures.map((value) => value / total);
    return {
        topShowExposureShare: Math.max(...shares),
        exposureHhi: shares.reduce((sum, share) => sum + share * share, 0),
    };
}

function buildVariant(
    row: OutcomeRow,
    concentrationRows: readonly ConcentrationRow[],
): DiscoveryVariantEvaluation {
    const impressionActors = number(row.impressionActors);
    const impressions = number(row.impressions);
    const distinctShows = number(row.distinctShows);
    const knownGeoImpressions = number(row.knownGeoImpressions);
    const explorationActors = number(row.explorationActors);
    const matchingConcentration = concentrationRows.filter(
        (item) =>
            item.experimentVariant === row.experimentVariant &&
            item.policyVersion === row.policyVersion,
    );

    return {
        experimentVariant: row.experimentVariant,
        policyVersion: row.policyVersion,
        qualifiedImpressionActors: impressionActors,
        impressions,
        distinctShows,
        primary: {
            actionableTicketIntent: {
                actors: number(row.actionableTicketIntentActors),
                rate: rate(
                    number(row.actionableTicketIntentActors),
                    impressionActors,
                ),
            },
            allTicketIntent: {
                actors: number(row.ticketIntentActors),
                rate: rate(number(row.ticketIntentActors), impressionActors),
            },
            soldOutDemand: {
                actors: number(row.soldOutDemandActors),
                rate: rate(number(row.soldOutDemandActors), impressionActors),
            },
            unknownAvailabilityTicketIntent: {
                actors: number(row.unknownAvailabilityTicketIntentActors),
                rate: rate(
                    number(row.unknownAvailabilityTicketIntentActors),
                    impressionActors,
                ),
            },
        },
        guardrails: {
            showDetail: {
                actors: number(row.detailActors),
                rate: rate(number(row.detailActors), impressionActors),
            },
            engagedShowCoverageRate: rate(
                number(row.detailEngagedShows),
                distinctShows,
            ),
            actionableResultCoverageRate: rate(
                number(row.actionableImpressions),
                impressions,
            ),
            geographicEligibilityRate: rate(
                number(row.geographicallyEligibleImpressions),
                knownGeoImpressions,
            ),
            geographicMeasurementCoverageRate: rate(
                knownGeoImpressions,
                impressions,
            ),
            newcomerExposureRate: rate(
                number(row.newcomerImpressions),
                impressions,
            ),
        },
        exploration: {
            selectedImpressions: number(row.explorationImpressions),
            exposedActors: explorationActors,
            detailEngagementRate: rate(
                number(row.explorationDetailActors),
                explorationActors,
            ),
            ticketIntentRate: rate(
                number(row.explorationTicketIntentActors),
                explorationActors,
            ),
        },
        rankingConcentration: concentration(matchingConcentration),
        dataQuality: {
            missingFeatureContextRate: rate(
                number(row.missingFeatureImpressions),
                impressions,
            ),
            latestImpressedAt: iso(row.latestImpressedAt),
            latestRecordedAt: iso(row.latestRecordedAt),
        },
    };
}

function distribution(
    count: Numeric,
    mean: number | null,
    p10: number | null,
    p50: number | null,
    p90: number | null,
): DistributionSummary {
    return { count: number(count), mean, p10, p50, p90 };
}

function featurePeriod(row: FeatureDistributionRow): FeaturePeriodSummary {
    return {
        snapshots: number(row.snapshots),
        prominence: distribution(
            row.snapshots,
            row.prominenceMean,
            row.prominenceP10,
            row.prominenceP50,
            row.prominenceP90,
        ),
        momentum: distribution(
            row.snapshots,
            row.momentumMean,
            row.momentumP10,
            row.momentumP50,
            row.momentumP90,
        ),
        growth: distribution(
            row.snapshots,
            row.growthMean,
            row.growthP10,
            row.growthP50,
            row.growthP90,
        ),
        confidence: distribution(
            row.snapshots,
            row.confidenceMean,
            row.confidenceP10,
            row.confidenceP50,
            row.confidenceP90,
        ),
        availability: {
            available: number(row.availableSnapshots),
            unknown: number(row.unknownSnapshots),
            unavailable: number(row.unavailableSnapshots),
        },
        staleSnapshots: number(row.staleSnapshots),
        latestAsOf: iso(row.latestAsOf),
        latestComputedAt: iso(row.latestComputedAt),
    };
}

function latestPolicy(
    variants: readonly DiscoveryVariantEvaluation[],
    variant: "control" | "candidate",
): DiscoveryVariantEvaluation | undefined {
    return variants
        .filter((item) => item.experimentVariant === variant)
        .sort((left, right) =>
            (right.dataQuality.latestImpressedAt ?? "").localeCompare(
                left.dataQuality.latestImpressedAt ?? "",
            ),
        )[0];
}

function decide(
    control: DiscoveryVariantEvaluation | undefined,
    candidate: DiscoveryVariantEvaluation | undefined,
    primaryDelta: number | null,
    detailDelta: number | null,
    coverageDelta: number | null,
    stale: boolean,
    observationDays: number,
): DiscoveryEvaluation["decision"] {
    const reasons: string[] = [];
    if (
        !control ||
        !candidate ||
        observationDays < MINIMUM_OBSERVATION_DAYS ||
        control.qualifiedImpressionActors < MINIMUM_ACTORS_PER_ARM ||
        candidate.qualifiedImpressionActors < MINIMUM_ACTORS_PER_ARM ||
        control.primary.allTicketIntent.actors <
            MINIMUM_TICKET_INTENT_ACTORS_PER_ARM ||
        candidate.primary.allTicketIntent.actors <
            MINIMUM_TICKET_INTENT_ACTORS_PER_ARM
    ) {
        reasons.push(
            `Each arm needs ${MINIMUM_OBSERVATION_DAYS} days, at least ${MINIMUM_ACTORS_PER_ARM} assignment-eligible impression actors, and ${MINIMUM_TICKET_INTENT_ACTORS_PER_ARM} ticket-intent actors.`,
        );
        return { status: "insufficient", reasons };
    }
    if (stale) reasons.push("Discovery feature inputs are stale.");
    if (
        candidate.guardrails.geographicEligibilityRate !== null &&
        candidate.guardrails.geographicEligibilityRate < 1
    ) {
        reasons.push("Candidate contains a geography eligibility violation.");
    }
    if (coverageDelta !== null && coverageDelta < -0.02) {
        reasons.push(
            "Candidate actionable result coverage is down more than 2 points.",
        );
    }
    if (
        reasons.some(
            (reason) =>
                reason.includes("violation") || reason.includes("2 points"),
        )
    ) {
        return { status: "rollback", reasons };
    }
    if (
        !stale &&
        primaryDelta !== null &&
        primaryDelta >= 0.05 &&
        (detailDelta === null || detailDelta >= 0) &&
        (coverageDelta === null || coverageDelta >= -0.02)
    ) {
        reasons.push(
            "Candidate meets the primary metric and configured guardrails.",
        );
        return { status: "ship", reasons };
    }
    reasons.push(
        "Candidate needs tuning or more conclusive guardrail results.",
    );
    return { status: "tune", reasons };
}

export function buildDiscoveryEvaluation(
    options: Required<DiscoveryEvaluationOptions>,
    outcomeRows: readonly OutcomeRow[],
    concentrationRows: readonly ConcentrationRow[],
    featureRows: readonly FeatureDistributionRow[],
): DiscoveryEvaluation {
    const end = new Date(options.now);
    const start = new Date(end.getTime() - options.days * DAY_MS);
    const eligibleRows = outcomeRows.filter(
        (row) => row.assignmentBucket === "eligible",
    );
    const variants = eligibleRows.map((row) =>
        buildVariant(row, concentrationRows),
    );
    const control = latestPolicy(variants, "control");
    const candidate = latestPolicy(variants, "candidate");
    const primaryDelta = relativeDelta(
        candidate?.primary.actionableTicketIntent.rate ?? null,
        control?.primary.actionableTicketIntent.rate ?? null,
    );
    const detailDelta = relativeDelta(
        candidate?.guardrails.showDetail.rate ?? null,
        control?.guardrails.showDetail.rate ?? null,
    );
    const coverageDelta = difference(
        candidate?.guardrails.actionableResultCoverageRate ?? null,
        control?.guardrails.actionableResultCoverageRate ?? null,
    );
    const currentRow = featureRows.find((row) => row.period === "current");
    const baselineRow = featureRows.find((row) => row.period === "baseline");
    const current = currentRow ? featurePeriod(currentRow) : null;
    const baseline = baselineRow ? featurePeriod(baselineRow) : null;
    const featureNames = [
        "prominence",
        "momentum",
        "growth",
        "confidence",
    ] as const;
    const meanShifts = Object.fromEntries(
        featureNames.map((feature) => [
            feature,
            difference(
                current?.[feature].mean ?? null,
                baseline?.[feature].mean ?? null,
            ),
        ]),
    ) as DiscoveryEvaluation["drift"]["meanShifts"];
    const shiftedFeatures = featureNames.filter(
        (feature) => Math.abs(meanShifts[feature] ?? 0) >= 0.1,
    );
    const latestComputedAt = current?.latestComputedAt
        ? new Date(current.latestComputedAt)
        : null;
    const stale =
        !current ||
        current.snapshots === 0 ||
        current.staleSnapshots > 0 ||
        !latestComputedAt ||
        end.getTime() - latestComputedAt.getTime() >
            FEATURE_STALE_HOURS * 60 * 60 * 1000;

    const actorTotal = (bucket: AssignmentBucket) =>
        outcomeRows
            .filter((row) => row.assignmentBucket === bucket)
            .reduce((sum, row) => sum + number(row.impressionActors), 0);

    return {
        window: {
            start: start.toISOString(),
            end: end.toISOString(),
            days: options.days,
        },
        contract: {
            primaryMetric:
                "actionable_ticket_intent_actors_per_qualified_impression_actor",
            minimumActorsPerArm: MINIMUM_ACTORS_PER_ARM,
            minimumTicketIntentActorsPerArm:
                MINIMUM_TICKET_INTENT_ACTORS_PER_ARM,
            minimumObservationDays: MINIMUM_OBSERVATION_DAYS,
            featureVersion: DISCOVERY_FEATURE_VERSION,
            featureStaleAfterHours: FEATURE_STALE_HOURS,
        },
        traffic: {
            assignmentEligibleActors: actorTotal("eligible"),
            bootstrapControlActors: actorTotal("bootstrap"),
            legacyUnknownActors: actorTotal("legacy_unknown"),
        },
        variants,
        comparison: {
            candidatePolicyVersion: candidate?.policyVersion ?? null,
            controlPolicyVersion: control?.policyVersion ?? null,
            primaryRelativeDelta: primaryDelta,
            detailRelativeDelta: detailDelta,
            actionableCoverageDelta: coverageDelta,
        },
        drift: {
            current,
            baseline,
            meanShifts,
            shiftedFeatures,
            stale,
        },
        decision: decide(
            control,
            candidate,
            primaryDelta,
            detailDelta,
            coverageDelta,
            stale,
            options.days,
        ),
    };
}

function buildOutcomeQuery(start: Date, end: Date): Prisma.Sql {
    return Prisma.sql`
        WITH qualified AS (
            SELECT
                i.event_id,
                i.entity_id,
                i.experiment_variant,
                i.policy_version,
                CASE
                    WHEN i.assignment_eligible IS TRUE THEN 'eligible'
                    WHEN i.assignment_reason = 'cookieless_bootstrap' THEN 'bootstrap'
                    ELSE 'legacy_unknown'
                END AS assignment_bucket,
                CASE
                    WHEN i.profile_id IS NOT NULL THEN 'profile:' || i.profile_id
                    ELSE 'anonymous:' || i.anonymous_visitor_id
                END AS actor_key,
                i.exploration_selected IS TRUE AS exploration_selected,
                i.distance_miles,
                i.max_distance_miles,
                i.availability_at_impression,
                i.feature_version,
                i.impressed_at,
                i.recorded_at,
                s.first_discovered_at,
                EXISTS (
                    SELECT 1
                    FROM discovery_engagement_events e
                    WHERE e.impression_event_id = i.event_id
                      AND e.engagement_type = 'show_detail'
                ) AS has_detail,
                EXISTS (
                    SELECT 1
                    FROM ticket_purchase_click_events t
                    WHERE t.discovery_impression_event_id = i.event_id
                ) AS has_ticket_intent
            FROM discovery_impression_events i
            LEFT JOIN shows s ON s.id = i.entity_id
            WHERE i.surface = 'near_you'
              AND i.entity_type = 'show'
              AND i.impressed_at >= ${start}
              AND i.impressed_at < ${end}
        )
        SELECT
            experiment_variant AS "experimentVariant",
            policy_version AS "policyVersion",
            assignment_bucket AS "assignmentBucket",
            COUNT(DISTINCT actor_key) AS "impressionActors",
            COUNT(*) AS impressions,
            COUNT(DISTINCT entity_id) AS "distinctShows",
            COUNT(DISTINCT actor_key) FILTER (WHERE has_detail) AS "detailActors",
            COUNT(DISTINCT entity_id) FILTER (WHERE has_detail) AS "detailEngagedShows",
            COUNT(DISTINCT actor_key) FILTER (WHERE has_ticket_intent) AS "ticketIntentActors",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE has_ticket_intent
                  AND availability_at_impression = 'available'
            ) AS "actionableTicketIntentActors",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE has_ticket_intent
                  AND availability_at_impression = 'unavailable'
            ) AS "soldOutDemandActors",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE has_ticket_intent
                  AND (
                    availability_at_impression = 'unknown'
                    OR availability_at_impression IS NULL
                  )
            ) AS "unknownAvailabilityTicketIntentActors",
            COUNT(*) FILTER (
                WHERE availability_at_impression = 'available'
            ) AS "actionableImpressions",
            COUNT(*) FILTER (
                WHERE availability_at_impression = 'unavailable'
            ) AS "unavailableImpressions",
            COUNT(*) FILTER (
                WHERE distance_miles IS NOT NULL
                  AND max_distance_miles IS NOT NULL
            ) AS "knownGeoImpressions",
            COUNT(*) FILTER (
                WHERE distance_miles <= max_distance_miles
            ) AS "geographicallyEligibleImpressions",
            COUNT(*) FILTER (
                WHERE first_discovered_at >= impressed_at - interval '28 days'
            ) AS "newcomerImpressions",
            COUNT(*) FILTER (WHERE exploration_selected) AS "explorationImpressions",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE exploration_selected
            ) AS "explorationActors",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE exploration_selected AND has_detail
            ) AS "explorationDetailActors",
            COUNT(DISTINCT actor_key) FILTER (
                WHERE exploration_selected AND has_ticket_intent
            ) AS "explorationTicketIntentActors",
            COUNT(*) FILTER (WHERE feature_version IS NULL) AS "missingFeatureImpressions",
            MAX(impressed_at) AS "latestImpressedAt",
            MAX(recorded_at) AS "latestRecordedAt"
        FROM qualified
        GROUP BY experiment_variant, policy_version, assignment_bucket
        ORDER BY experiment_variant, policy_version, assignment_bucket
    `;
}

function buildConcentrationQuery(start: Date, end: Date): Prisma.Sql {
    return Prisma.sql`
        SELECT
            experiment_variant AS "experimentVariant",
            policy_version AS "policyVersion",
            entity_id AS "entityId",
            COUNT(*) AS impressions
        FROM discovery_impression_events
        WHERE surface = 'near_you'
          AND entity_type = 'show'
          AND assignment_eligible IS TRUE
          AND impressed_at >= ${start}
          AND impressed_at < ${end}
        GROUP BY experiment_variant, policy_version, entity_id
    `;
}

function buildFeatureDistributionQuery(start: Date, end: Date): Prisma.Sql {
    const baselineStart = new Date(
        start.getTime() - (end.getTime() - start.getTime()),
    );
    return Prisma.sql`
        WITH periods(period, period_start, period_end) AS (
            VALUES
                ('current'::text, ${start}::timestamptz, ${end}::timestamptz),
                ('baseline'::text, ${baselineStart}::timestamptz, ${start}::timestamptz)
        ),
        latest AS (
            SELECT
                p.period,
                p.period_end,
                f.*,
                ROW_NUMBER() OVER (
                    PARTITION BY p.period, f.show_id
                    ORDER BY f.as_of DESC, f.computed_at DESC, f.id DESC
                ) AS snapshot_rank
            FROM periods p
            JOIN discovery_show_feature_snapshots f
              ON f.feature_version = ${DISCOVERY_FEATURE_VERSION}
             AND f.as_of < p.period_end
        )
        SELECT
            period,
            COUNT(*) AS snapshots,
            AVG(prominence) AS "prominenceMean",
            percentile_cont(0.1) WITHIN GROUP (ORDER BY prominence) AS "prominenceP10",
            percentile_cont(0.5) WITHIN GROUP (ORDER BY prominence) AS "prominenceP50",
            percentile_cont(0.9) WITHIN GROUP (ORDER BY prominence) AS "prominenceP90",
            AVG(momentum) AS "momentumMean",
            percentile_cont(0.1) WITHIN GROUP (ORDER BY momentum) AS "momentumP10",
            percentile_cont(0.5) WITHIN GROUP (ORDER BY momentum) AS "momentumP50",
            percentile_cont(0.9) WITHIN GROUP (ORDER BY momentum) AS "momentumP90",
            AVG(growth) AS "growthMean",
            percentile_cont(0.1) WITHIN GROUP (ORDER BY growth) AS "growthP10",
            percentile_cont(0.5) WITHIN GROUP (ORDER BY growth) AS "growthP50",
            percentile_cont(0.9) WITHIN GROUP (ORDER BY growth) AS "growthP90",
            AVG(confidence) AS "confidenceMean",
            percentile_cont(0.1) WITHIN GROUP (ORDER BY confidence) AS "confidenceP10",
            percentile_cont(0.5) WITHIN GROUP (ORDER BY confidence) AS "confidenceP50",
            percentile_cont(0.9) WITHIN GROUP (ORDER BY confidence) AS "confidenceP90",
            COUNT(*) FILTER (WHERE availability = 'available') AS "availableSnapshots",
            COUNT(*) FILTER (WHERE availability = 'unknown') AS "unknownSnapshots",
            COUNT(*) FILTER (WHERE availability = 'unavailable') AS "unavailableSnapshots",
            COUNT(*) FILTER (
                WHERE as_of < period_end - interval '48 hours'
            ) AS "staleSnapshots",
            MAX(as_of) AS "latestAsOf",
            MAX(computed_at) AS "latestComputedAt"
        FROM latest
        WHERE snapshot_rank = 1
        GROUP BY period
    `;
}

export async function getDiscoveryEvaluation(
    options: DiscoveryEvaluationOptions = {},
): Promise<DiscoveryEvaluation> {
    const days = options.days ?? 14;
    if (!Number.isInteger(days) || days < 1 || days > 90) {
        throw new RangeError("days must be an integer between 1 and 90");
    }
    const now = options.now ? new Date(options.now) : new Date();
    if (Number.isNaN(now.getTime())) throw new RangeError("now must be valid");
    const start = new Date(now.getTime() - days * DAY_MS);
    const [outcomes, concentrations, features] = await Promise.all([
        db.$queryRaw<OutcomeRow[]>(buildOutcomeQuery(start, now)),
        db.$queryRaw<ConcentrationRow[]>(buildConcentrationQuery(start, now)),
        db.$queryRaw<FeatureDistributionRow[]>(
            buildFeatureDistributionQuery(start, now),
        ),
    ]);
    return buildDiscoveryEvaluation(
        { days, now },
        outcomes,
        concentrations,
        features,
    );
}
