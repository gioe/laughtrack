import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { NextRequest, NextResponse } from "next/server";
import {
    applyDiscoveryWriteRateLimit,
    isPolicyVersion,
    isUuid,
    parseBatch,
    parseEventTime,
    resolveDiscoveryActor,
    setAnonymousVisitorCookie,
} from "../shared";
import { rateLimitHeaders } from "@/lib/rateLimit";
import type {
    DiscoveryAssignmentReason,
    DiscoveryAvailabilityAtImpression,
} from "@/lib/discovery/telemetry";

const ENTITY_TYPE = "show";
const SURFACE = "near_you";
const EXPERIMENT_VARIANTS = new Set(["control", "candidate"]);
const ASSIGNMENT_REASONS = new Set<DiscoveryAssignmentReason>([
    "stable_actor_assignment",
    "cookieless_bootstrap",
]);
const AVAILABILITY_STATES = new Set<DiscoveryAvailabilityAtImpression>([
    "available",
    "unknown",
    "unavailable",
]);

type ImpressionInput = {
    eventId: string;
    entityType: typeof ENTITY_TYPE;
    entityId: number;
    surface: typeof SURFACE;
    policyVersion: string;
    experimentVariant: "control" | "candidate";
    rank: number;
    impressedAt: Date;
    assignmentEligible: boolean;
    assignmentReason: DiscoveryAssignmentReason;
    explorationSelected: boolean;
    distanceMiles: number | null;
    maxDistanceMiles: number;
    availabilityAtImpression: DiscoveryAvailabilityAtImpression;
    featureVersion: string | null;
};

function parseImpression(value: unknown): ImpressionInput | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return null;
    }
    const data = value as Record<string, unknown>;
    const entityId = data.entityId;
    const rank = data.rank;
    const impressedAt = parseEventTime(data.impressedAt);
    const distanceMiles = data.distanceMiles;
    const maxDistanceMiles = data.maxDistanceMiles;
    const featureVersion = data.featureVersion;

    if (
        !isUuid(data.eventId) ||
        data.entityType !== ENTITY_TYPE ||
        typeof entityId !== "number" ||
        !Number.isSafeInteger(entityId) ||
        entityId <= 0 ||
        data.surface !== SURFACE ||
        !isPolicyVersion(data.policyVersion) ||
        typeof data.experimentVariant !== "string" ||
        !EXPERIMENT_VARIANTS.has(data.experimentVariant) ||
        typeof rank !== "number" ||
        !Number.isSafeInteger(rank) ||
        rank < 1 ||
        rank > 1000 ||
        typeof data.assignmentEligible !== "boolean" ||
        typeof data.assignmentReason !== "string" ||
        !ASSIGNMENT_REASONS.has(
            data.assignmentReason as DiscoveryAssignmentReason,
        ) ||
        data.assignmentEligible !==
            (data.assignmentReason === "stable_actor_assignment") ||
        typeof data.explorationSelected !== "boolean" ||
        (distanceMiles !== null &&
            (typeof distanceMiles !== "number" ||
                !Number.isFinite(distanceMiles) ||
                distanceMiles < 0)) ||
        typeof maxDistanceMiles !== "number" ||
        !Number.isFinite(maxDistanceMiles) ||
        maxDistanceMiles <= 0 ||
        typeof data.availabilityAtImpression !== "string" ||
        !AVAILABILITY_STATES.has(
            data.availabilityAtImpression as DiscoveryAvailabilityAtImpression,
        ) ||
        (featureVersion !== null && !isPolicyVersion(featureVersion)) ||
        (!data.assignmentEligible &&
            (data.experimentVariant !== "control" ||
                data.explorationSelected)) ||
        (data.explorationSelected && data.experimentVariant !== "candidate") ||
        !impressedAt
    ) {
        return null;
    }

    return {
        eventId: data.eventId,
        entityType: ENTITY_TYPE,
        entityId,
        surface: SURFACE,
        policyVersion: data.policyVersion,
        experimentVariant: data.experimentVariant as "control" | "candidate",
        rank,
        impressedAt,
        assignmentEligible: data.assignmentEligible,
        assignmentReason: data.assignmentReason as DiscoveryAssignmentReason,
        explorationSelected: data.explorationSelected,
        distanceMiles: distanceMiles as number | null,
        maxDistanceMiles,
        availabilityAtImpression:
            data.availabilityAtImpression as DiscoveryAvailabilityAtImpression,
        featureVersion: featureVersion as string | null,
    };
}

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    let payload: unknown;
    try {
        payload = await req.json();
    } catch {
        return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }

    const rawEvents = parseBatch(payload);
    const events = rawEvents?.map(parseImpression) ?? [];
    if (!rawEvents || events.some((event) => event === null)) {
        return NextResponse.json(
            { error: "Invalid discovery impression batch" },
            { status: 400 },
        );
    }
    const parsedEvents = events as ImpressionInput[];

    const actor = await resolveDiscoveryActor(req);
    const rateLimit = await applyDiscoveryWriteRateLimit(
        req,
        actor,
        "discovery-impressions",
    );
    if (rateLimit instanceof NextResponse) return rateLimit;

    const entityIds = [...new Set(parsedEvents.map((event) => event.entityId))];
    const shows = await db.show.findMany({
        where: { id: { in: entityIds } },
        select: { id: true },
    });
    const foundIds = new Set(shows.map((show) => show.id));
    if (entityIds.some((id) => !foundIds.has(id))) {
        return NextResponse.json(
            { error: "Discovery impression references an unknown entity" },
            { status: 400, headers: rateLimitHeaders(rateLimit) },
        );
    }

    const result = await db.discoveryImpressionEvent.createMany({
        data: parsedEvents.map((event) => ({
            ...event,
            profileId: actor.profileId,
            anonymousVisitorId: actor.anonymousVisitorId,
        })),
        skipDuplicates: true,
    });
    const response = NextResponse.json(
        { accepted: parsedEvents.length, inserted: result.count },
        { status: 201, headers: rateLimitHeaders(rateLimit) },
    );
    setAnonymousVisitorCookie(response, actor);
    return response;
});
