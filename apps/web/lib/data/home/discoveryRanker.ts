import { DISCOVERY_FEATURE_VERSION } from "@/lib/discovery/features";
import { ShowDTO } from "@/objects/class/show/show.interface";

export const NEAR_YOU_CONTROL_POLICY_VERSION = "near-you-control-v1";
export const NEAR_YOU_CANDIDATE_POLICY_VERSION = "near-you-candidate-v1";
export const NEAR_YOU_RANKER_FLAG = "NEAR_YOU_DISCOVERY_RANKER_ENABLED";

const CANDIDATE_ALLOCATION = 0.5;
const EXPLORATION_ALLOCATION = 0.1;
const DATE_HORIZON_MS = 30 * 24 * 60 * 60 * 1000;

export type NearYouExperimentVariant = "control" | "candidate";

export interface NearYouDiscoveryPolicy {
    experimentVariant: NearYouExperimentVariant;
    policyVersion: string;
}

export interface NearYouFeatureSnapshot {
    featureVersion: string;
    asOf: Date;
    prominence: number;
    momentum: number;
    growth: number;
    confidence: number;
    availability: "available" | "unknown" | "unavailable";
}

export interface NearYouRankingCandidate {
    show: ShowDTO;
    snapshot?: NearYouFeatureSnapshot | null;
    /**
     * 1 for a known favorite-lineup match, 0 for a signed-in non-match, and
     * 0.5 when affinity is unavailable.
     */
    affinity?: number;
}

export interface NearYouRankingContext {
    now: Date;
    maxDistanceMiles: number;
    actorKey: string;
    take?: number;
}

interface ScoredCandidate {
    candidate: NearYouRankingCandidate;
    score: number;
    prominence: number;
}

function clamp(value: number, minimum = 0, maximum = 1): number {
    return Math.min(Math.max(value, minimum), maximum);
}

/**
 * A small deterministic hash is sufficient for experiment bucketing. The
 * namespace is included in the input so changing policy versions does not
 * silently reuse an unrelated allocation.
 */
function stableFraction(namespace: string, actorKey: string): number {
    let hash = 0x811c9dc5;
    const input = `${namespace}:${actorKey}`;
    for (let index = 0; index < input.length; index += 1) {
        hash ^= input.charCodeAt(index);
        hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0) / 0x1_0000_0000;
}

export function isNearYouRankerEnabled(
    value = process.env[NEAR_YOU_RANKER_FLAG],
): boolean {
    return value === "1" || value === "true";
}

export function resolveNearYouDiscoveryPolicy({
    enabled,
    actorKey,
}: {
    enabled: boolean;
    actorKey?: string | null;
}): NearYouDiscoveryPolicy {
    const isCandidate =
        enabled &&
        Boolean(actorKey) &&
        stableFraction(
            `${NEAR_YOU_CANDIDATE_POLICY_VERSION}:assignment`,
            actorKey as string,
        ) < CANDIDATE_ALLOCATION;

    return isCandidate
        ? {
              experimentVariant: "candidate",
              policyVersion: NEAR_YOU_CANDIDATE_POLICY_VERSION,
          }
        : {
              experimentVariant: "control",
              policyVersion: NEAR_YOU_CONTROL_POLICY_VERSION,
          };
}

export function isNearYouExplorationActor(actorKey: string): boolean {
    return (
        stableFraction(
            `${NEAR_YOU_CANDIDATE_POLICY_VERSION}:exploration`,
            actorKey,
        ) < EXPLORATION_ALLOCATION
    );
}

function effectiveSnapshot(
    snapshot: NearYouFeatureSnapshot | null | undefined,
    now: Date,
): NearYouFeatureSnapshot {
    if (
        !snapshot ||
        snapshot.featureVersion !== DISCOVERY_FEATURE_VERSION ||
        snapshot.asOf.getTime() > now.getTime()
    ) {
        return {
            featureVersion: DISCOVERY_FEATURE_VERSION,
            asOf: now,
            prominence: 0.5,
            momentum: 0.5,
            growth: 0.5,
            confidence: 0,
            availability: "unknown",
        };
    }
    return snapshot;
}

function confidenceDamped(value: number, confidence: number): number {
    return 0.5 + (clamp(value) - 0.5) * clamp(confidence);
}

function scoreCandidate(
    candidate: NearYouRankingCandidate,
    context: NearYouRankingContext,
): ScoredCandidate | null {
    const { show } = candidate;
    if (
        show.soldOut ||
        show.date.getTime() <= context.now.getTime() ||
        (show.distanceMiles !== null &&
            show.distanceMiles !== undefined &&
            show.distanceMiles > context.maxDistanceMiles)
    ) {
        return null;
    }

    const snapshot = effectiveSnapshot(candidate.snapshot, context.now);
    if (snapshot.availability === "unavailable") return null;

    const confidence = clamp(snapshot.confidence);
    const geography =
        show.distanceMiles === null || show.distanceMiles === undefined
            ? 0.5
            : clamp(1 - show.distanceMiles / context.maxDistanceMiles);
    const date = clamp(
        1 - (show.date.getTime() - context.now.getTime()) / DATE_HORIZON_MS,
    );
    const affinity = clamp(candidate.affinity ?? 0.5);
    const momentum = confidenceDamped(snapshot.momentum, confidence);
    const growth = confidenceDamped(snapshot.growth, confidence);
    const prominence = confidenceDamped(snapshot.prominence, confidence);

    return {
        candidate,
        prominence,
        score:
            geography * 0.28 +
            date * 0.17 +
            affinity * 0.15 +
            momentum * 0.13 +
            growth * 0.17 +
            prominence * 0.1,
    };
}

function compareScoredCandidates(
    left: ScoredCandidate,
    right: ScoredCandidate,
): number {
    const scoreDelta = right.score - left.score;
    if (scoreDelta !== 0) return scoreDelta;

    const dateDelta =
        left.candidate.show.date.getTime() -
        right.candidate.show.date.getTime();
    if (dateDelta !== 0) return dateDelta;

    return left.candidate.show.id - right.candidate.show.id;
}

export function rankNearYouCandidates(
    candidates: readonly NearYouRankingCandidate[],
    context: NearYouRankingContext,
): ShowDTO[] {
    const take = Math.max(0, context.take ?? 8);
    if (take === 0) return [];

    const ranked = candidates
        .map((candidate) => scoreCandidate(candidate, context))
        .filter((candidate): candidate is ScoredCandidate => candidate !== null)
        .sort(compareScoredCandidates);
    const selected = ranked.slice(0, take);

    if (
        selected.length === take &&
        ranked.length > take &&
        isNearYouExplorationActor(context.actorKey)
    ) {
        const highestSelectedProminence = Math.max(
            ...selected.map((candidate) => candidate.prominence),
        );
        const explorationPool = ranked
            .slice(take)
            .filter(
                (candidate) => candidate.prominence < highestSelectedProminence,
            )
            .sort((left, right) => {
                const leftBucket = stableFraction(
                    `${NEAR_YOU_CANDIDATE_POLICY_VERSION}:show-exploration`,
                    `${context.actorKey}:${left.candidate.show.id}`,
                );
                const rightBucket = stableFraction(
                    `${NEAR_YOU_CANDIDATE_POLICY_VERSION}:show-exploration`,
                    `${context.actorKey}:${right.candidate.show.id}`,
                );
                return (
                    leftBucket - rightBucket ||
                    left.candidate.show.id - right.candidate.show.id
                );
            });

        if (explorationPool[0]) {
            selected[selected.length - 1] = explorationPool[0];
        }
    }

    return selected.map(({ candidate }) => candidate.show);
}
