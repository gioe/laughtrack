import {
    getDefaultDiscoveryRailPolicy,
    type DiscoveryPlatform,
    type DiscoveryRailKey,
    type DiscoveryRailPolicyDto,
    type DiscoveryRailPolicyRailDto,
} from "./railPolicy";

export const DISCOVERY_RAIL_PLAN_VERSION = 1 as const;

export type DiscoveryRailItemId = string | number;

export interface DiscoveryRailPayload {
    payloadKey: string;
    items: readonly { id?: DiscoveryRailItemId | null }[];
}

export type DiscoveryRailPayloadMap = Partial<
    Record<DiscoveryRailKey, DiscoveryRailPayload>
>;

export interface DiscoveryRailPlanEntry {
    railKey: DiscoveryRailKey;
    payloadKey: string;
    position: number;
    itemIds: string[];
}

export interface DiscoveryRailPlan {
    version: typeof DISCOVERY_RAIL_PLAN_VERSION;
    catalogVersion: DiscoveryRailPolicyDto["catalogVersion"];
    policyVersion: number;
    platform: DiscoveryPlatform;
    cycleIndex: number;
    rails: DiscoveryRailPlanEntry[];
}

export interface SelectDiscoveryRailPlanOptions {
    policy: DiscoveryRailPolicyDto;
    actorKey: string;
    cycleIndex: number;
    payloads: DiscoveryRailPayloadMap;
}

export type DiscoveryRailPolicyLoader = (
    platform: DiscoveryPlatform,
) => Promise<DiscoveryRailPolicyDto>;

const SHOW_RAIL_KEYS = new Set<DiscoveryRailKey>([
    "shows_tonight",
    "followed_comedian_shows",
    "trending_this_week",
    "nearby_shows",
    "just_passing_through",
    "rare_returns",
    "only_chance_nearby",
    "newly_added",
    "starting_to_buzz",
    "catch_them_early",
    "from_your_podcasts",
    "because_you_follow_them",
]);

/**
 * Converts a caller-supplied observation time to the policy's UTC cycle index.
 * Keeping the clock outside the selector makes plan selection fully pure.
 */
export function getDiscoveryRailCycleIndex(
    observedAt: Date | number,
    cycleCadenceHours: number,
): number {
    const timestamp =
        observedAt instanceof Date ? observedAt.getTime() : observedAt;
    return Math.floor(timestamp / (cycleCadenceHours * 60 * 60 * 1000));
}

function stableHash(value: string): number {
    let hash = 0x811c9dc5;
    for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 0x01000193);
    }
    // Avalanche the FNV state so modulo-based weighted buckets also use
    // well-distributed high bits when seeds share long suffixes.
    hash ^= hash >>> 16;
    hash = Math.imul(hash, 0x85ebca6b);
    hash ^= hash >>> 13;
    hash = Math.imul(hash, 0xc2b2ae35);
    hash ^= hash >>> 16;
    return hash >>> 0;
}

function chooseWeightedRail(
    rails: readonly DiscoveryRailPolicyRailDto[],
    seed: string,
): DiscoveryRailPolicyRailDto {
    const totalWeight = rails.reduce((total, rail) => total + rail.weight, 0);
    let bucket = stableHash(seed) % totalWeight;

    for (const rail of rails) {
        if (bucket < rail.weight) return rail;
        bucket -= rail.weight;
    }

    // Policy validation guarantees a non-empty pool with positive weights.
    return rails[rails.length - 1];
}

function selectPolicyRails({
    policy,
    actorKey,
    cycleIndex,
}: Pick<
    SelectDiscoveryRailPlanOptions,
    "policy" | "actorKey" | "cycleIndex"
>): DiscoveryRailPolicyRailDto[] {
    const enabledRails = policy.rails.filter((rail) => rail.enabled);
    const rotationPools = new Map<string, DiscoveryRailPolicyRailDto[]>();

    for (const rail of enabledRails) {
        if (rail.rotationPool === null) continue;
        const members = rotationPools.get(rail.rotationPool) ?? [];
        members.push(rail);
        rotationPools.set(rail.rotationPool, members);
    }

    const selected = enabledRails
        .filter((rail) => rail.rotationPool === null)
        .map((rail, policyIndex) => ({ rail, policyIndex }));

    const selectedPools = new Set<string>();
    enabledRails.forEach((rail, policyIndex) => {
        const pool = rail.rotationPool;
        if (pool === null || selectedPools.has(pool)) return;
        selectedPools.add(pool);

        const members = rotationPools.get(pool);
        if (!members?.length) return;

        selected.push({
            rail: chooseWeightedRail(
                members,
                `${policy.platform}:${actorKey}:${policy.version}:${cycleIndex}:${pool}`,
            ),
            policyIndex,
        });
    });

    return selected
        .sort(
            (left, right) =>
                left.rail.position - right.rail.position ||
                left.policyIndex - right.policyIndex,
        )
        .map(({ rail }) => rail);
}

/** Builds a JSON-safe, ordered plan without mutating the policy or payloads. */
export function selectDiscoveryRailPlan({
    policy,
    actorKey,
    cycleIndex,
    payloads,
}: SelectDiscoveryRailPlanOptions): DiscoveryRailPlan {
    const seenShowIds = new Set<string>();
    const rails: DiscoveryRailPlanEntry[] = [];

    for (const selectedRail of selectPolicyRails({
        policy,
        actorKey,
        cycleIndex,
    })) {
        const payload = payloads[selectedRail.railKey];
        if (!payload) continue;

        const itemIds = payload.items
            .flatMap((item) =>
                item.id === undefined || item.id === null
                    ? []
                    : [String(item.id)],
            )
            .filter((itemId) => {
                if (!SHOW_RAIL_KEYS.has(selectedRail.railKey)) return true;
                if (seenShowIds.has(itemId)) return false;
                seenShowIds.add(itemId);
                return true;
            });

        if (itemIds.length === 0) continue;
        rails.push({
            railKey: selectedRail.railKey,
            payloadKey: payload.payloadKey,
            position: selectedRail.position,
            itemIds,
        });
    }

    return {
        version: DISCOVERY_RAIL_PLAN_VERSION,
        catalogVersion: policy.catalogVersion,
        policyVersion: policy.version,
        platform: policy.platform,
        cycleIndex,
        rails,
    };
}

export async function loadDiscoveryRailPolicyWithFallback(
    platform: DiscoveryPlatform,
    loadPolicy: DiscoveryRailPolicyLoader,
): Promise<DiscoveryRailPolicyDto> {
    try {
        return await loadPolicy(platform);
    } catch {
        return getDefaultDiscoveryRailPolicy(platform);
    }
}
