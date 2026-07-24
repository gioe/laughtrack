export type DiscoveryAssignmentReason =
    | "stable_actor_assignment"
    | "cookieless_bootstrap";

export type DiscoveryAvailabilityAtImpression =
    | "available"
    | "unknown"
    | "unavailable";

export interface DiscoveryShowImpressionContext {
    assignmentEligible: boolean;
    assignmentReason: DiscoveryAssignmentReason;
    explorationSelected: boolean;
    distanceMiles: number | null;
    maxDistanceMiles: number;
    availabilityAtImpression: DiscoveryAvailabilityAtImpression;
    featureVersion: string | null;
}

export type DiscoveryShowImpressionContexts = Record<
    number,
    DiscoveryShowImpressionContext
>;
