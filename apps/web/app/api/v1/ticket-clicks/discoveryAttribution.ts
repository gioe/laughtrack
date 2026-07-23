import { db } from "@/lib/db";

export type DiscoveryTicketAttribution = {
    discoveryImpressionEventId: string;
    discoverySurface: string;
    discoveryPolicyVersion: string;
    discoveryExperimentVariant: string;
    discoveryRank: number;
};

export const NO_DISCOVERY_TICKET_ATTRIBUTION = {
    discoveryImpressionEventId: null,
    discoverySurface: null,
    discoveryPolicyVersion: null,
    discoveryExperimentVariant: null,
    discoveryRank: null,
} as const;

const UUID_PATTERN =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function parseImpressionId(value: unknown): string | null {
    return typeof value === "string" && UUID_PATTERN.test(value) ? value : null;
}

export async function resolveDiscoveryTicketAttribution({
    impressionId,
    showId,
    profileId,
    anonymousVisitorId,
    retryMissing = false,
    adoptAnonymousVisitorId,
}: {
    impressionId: string;
    showId: number;
    profileId: string | null;
    anonymousVisitorId: string | null;
    retryMissing?: boolean;
    adoptAnonymousVisitorId?: (anonymousVisitorId: string) => void;
}): Promise<DiscoveryTicketAttribution | null> {
    let impression = null;
    const attempts = retryMissing ? 4 : 1;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
        impression = await db.discoveryImpressionEvent.findUnique({
            where: { eventId: impressionId },
            select: {
                eventId: true,
                entityType: true,
                entityId: true,
                profileId: true,
                anonymousVisitorId: true,
                surface: true,
                policyVersion: true,
                experimentVariant: true,
                rank: true,
            },
        });
        if (impression || attempt === attempts - 1) break;
        await new Promise((resolve) => setTimeout(resolve, 25));
    }

    if (
        !impression ||
        impression.entityType !== "show" ||
        impression.entityId !== showId
    ) {
        return null;
    }

    const profileOwnsImpression =
        profileId !== null && impression.profileId === profileId;
    const anonymousVisitorOwnsImpression =
        anonymousVisitorId !== null &&
        impression.anonymousVisitorId === anonymousVisitorId;
    const canAdoptFirstAnonymousVisitor =
        profileId === null &&
        anonymousVisitorId === null &&
        impression.profileId === null &&
        impression.anonymousVisitorId !== null &&
        adoptAnonymousVisitorId !== undefined;
    if (canAdoptFirstAnonymousVisitor) {
        adoptAnonymousVisitorId(impression.anonymousVisitorId);
    }
    if (
        !profileOwnsImpression &&
        !anonymousVisitorOwnsImpression &&
        !canAdoptFirstAnonymousVisitor
    ) {
        return null;
    }

    return {
        discoveryImpressionEventId: impression.eventId,
        discoverySurface: impression.surface,
        discoveryPolicyVersion: impression.policyVersion,
        discoveryExperimentVariant: impression.experimentVariant,
        discoveryRank: impression.rank,
    };
}
