import { db } from "@/lib/db";
import { withRequestMetrics } from "@/lib/metrics";
import { rateLimitHeaders } from "@/lib/rateLimit";
import { NextRequest, NextResponse } from "next/server";
import {
    applyDiscoveryWriteRateLimit,
    isUuid,
    parseBatch,
    parseEventTime,
    resolveDiscoveryActor,
    setAnonymousVisitorCookie,
} from "../shared";

const ENGAGEMENT_TYPE = "show_detail";

type EngagementInput = {
    eventId: string;
    impressionEventId: string;
    engagementType: typeof ENGAGEMENT_TYPE;
    engagedAt: Date;
};

function parseEngagement(value: unknown): EngagementInput | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return null;
    }
    const data = value as Record<string, unknown>;
    const engagedAt = parseEventTime(data.engagedAt);
    if (
        !isUuid(data.eventId) ||
        !isUuid(data.impressionEventId) ||
        data.engagementType !== ENGAGEMENT_TYPE ||
        !engagedAt
    ) {
        return null;
    }
    return {
        eventId: data.eventId,
        impressionEventId: data.impressionEventId,
        engagementType: ENGAGEMENT_TYPE,
        engagedAt,
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
    const events = rawEvents?.map(parseEngagement) ?? [];
    if (!rawEvents || events.some((event) => event === null)) {
        return NextResponse.json(
            { error: "Invalid discovery engagement batch" },
            { status: 400 },
        );
    }
    const parsedEvents = events as EngagementInput[];

    const actor = await resolveDiscoveryActor(req);
    const rateLimit = await applyDiscoveryWriteRateLimit(
        req,
        actor,
        "discovery-engagements",
    );
    if (rateLimit instanceof NextResponse) return rateLimit;

    const impressionIds = [
        ...new Set(parsedEvents.map((event) => event.impressionEventId)),
    ];
    let impressions = await db.discoveryImpressionEvent.findMany({
        where: { eventId: { in: impressionIds } },
        select: {
            eventId: true,
            profileId: true,
            anonymousVisitorId: true,
        },
    });
    for (
        let attempt = 1;
        impressions.length < impressionIds.length && attempt < 4;
        attempt += 1
    ) {
        await new Promise((resolve) => setTimeout(resolve, 25));
        impressions = await db.discoveryImpressionEvent.findMany({
            where: { eventId: { in: impressionIds } },
            select: {
                eventId: true,
                profileId: true,
                anonymousVisitorId: true,
            },
        });
    }

    let effectiveActor = actor;
    if (
        !actor.profileId &&
        actor.shouldSetAnonymousCookie &&
        impressions.length === impressionIds.length
    ) {
        const anonymousIds = new Set(
            impressions
                .filter((impression) => impression.profileId === null)
                .map((impression) => impression.anonymousVisitorId)
                .filter((id): id is string => id !== null),
        );
        if (
            anonymousIds.size === 1 &&
            impressions.every((impression) => impression.profileId === null)
        ) {
            effectiveActor = {
                ...actor,
                anonymousVisitorId: [...anonymousIds][0],
            };
        }
    }
    const ownedImpressionIds = new Set(
        impressions
            .filter(
                (impression) =>
                    (!!effectiveActor.profileId &&
                        impression.profileId === effectiveActor.profileId) ||
                    impression.anonymousVisitorId ===
                        effectiveActor.anonymousVisitorId,
            )
            .map((impression) => impression.eventId),
    );
    if (
        impressionIds.some(
            (impressionId) => !ownedImpressionIds.has(impressionId),
        )
    ) {
        return NextResponse.json(
            {
                error: "Discovery engagement references an unavailable impression",
            },
            { status: 400, headers: rateLimitHeaders(rateLimit) },
        );
    }

    const result = await db.discoveryEngagementEvent.createMany({
        data: parsedEvents,
        skipDuplicates: true,
    });
    const response = NextResponse.json(
        { accepted: parsedEvents.length, inserted: result.count },
        { status: 201, headers: rateLimitHeaders(rateLimit) },
    );
    setAnonymousVisitorCookie(response, effectiveActor);
    return response;
});
