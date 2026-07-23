import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import {
    RATE_LIMITS,
    checkRateLimit,
    getClientIp,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import {
    affiliateRulesFromEnv,
    isOriginAllowed,
    resolveAffiliateDestination,
} from "@/lib/affiliate/affiliateRouting";
import { Prisma } from "@prisma/client";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import {
    type DiscoveryTicketAttribution,
    NO_DISCOVERY_TICKET_ATTRIBUTION,
    parseImpressionId,
    resolveDiscoveryTicketAttribution,
} from "../../ticket-clicks/discoveryAttribution";

const ANON_COOKIE = "lt_anon_visitor_id";
const ANON_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 395;
const SOURCE_SURFACES = new Set([
    "show_detail",
    "show_card",
    "compact_show_card",
    "ios_show_detail",
]);

function parsePositiveInt(value: string | null): number | null {
    if (!value) return null;
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed <= 0) return null;
    return Number.isSafeInteger(parsed) ? parsed : null;
}

function parseSourceSurface(value: string | null): string | null {
    return value && SOURCE_SURFACES.has(value) ? value : null;
}

function getAnonymousVisitorId(req: NextRequest): {
    id: string;
    shouldSetCookie: boolean;
} {
    const existing = req.cookies.get(ANON_COOKIE)?.value;
    if (existing && existing.length <= 128) {
        return { id: existing, shouldSetCookie: false };
    }
    return { id: randomUUID(), shouldSetCookie: true };
}

async function applyTicketClickRateLimit(
    req: NextRequest,
    profileId: string | null,
) {
    const key = profileId
        ? `ticket-clicks:profile:${profileId}`
        : `ticket-clicks:anon-ip:${getClientIp(req)}`;
    const rl = await checkRateLimit(key, RATE_LIMITS.publicRead);
    if (!rl.allowed) return rateLimitResponse(rl);
    return rl;
}

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const showId = parsePositiveInt(searchParams.get("showId"));
    const clubId = parsePositiveInt(searchParams.get("clubId"));
    const sourceSurface = parseSourceSurface(searchParams.get("surface"));
    const suppliedImpressionId = searchParams.get("impressionId");
    const impressionId = parseImpressionId(suppliedImpressionId);
    const destination = resolveAffiliateDestination({
        destinationUrl: searchParams.get("url") ?? "",
        rules: affiliateRulesFromEnv(),
    });

    if (!showId || !clubId || !sourceSurface) {
        return NextResponse.json(
            { error: "Invalid outbound ticket payload" },
            { status: 400 },
        );
    }

    if (!destination.ok || !destination.originalUrl || !destination.routedUrl) {
        return NextResponse.json(
            { error: "Invalid destination URL" },
            { status: 400 },
        );
    }

    const show = await db.show.findUnique({
        where: { id: showId },
        select: {
            id: true,
            clubId: true,
            tickets: { select: { purchaseUrl: true } },
        },
    });
    if (!show) {
        return NextResponse.json({ error: "Show not found" }, { status: 404 });
    }
    if (show.clubId !== clubId) {
        return NextResponse.json(
            { error: "Club does not match show" },
            { status: 400 },
        );
    }

    // Prevent open redirect: showId/clubId are enumerable public ints, so the
    // show/club-match guard above does not stop a phishing link off the trusted
    // apex domain. Require the original url's origin to match one of the show's
    // real ticket purchaseUrl origins. Affiliate rewrites preserve the host, so
    // validate the ORIGINAL (pre-rewrite) url. The purchaseUrls come from the
    // show query above, so this adds no extra DB round trip.
    if (
        !isOriginAllowed(
            destination.originalUrl,
            show.tickets.map((ticket) => ticket.purchaseUrl),
        )
    ) {
        return NextResponse.json(
            { error: "Destination URL not permitted for show" },
            { status: 400 },
        );
    }

    const authCtx = await resolveAuth(req);
    const profileId =
        authCtx && authCtx !== PROFILE_MISSING ? authCtx.profileId : null;
    const rl = await applyTicketClickRateLimit(req, profileId);
    if (rl instanceof NextResponse) return rl;

    const anonymousVisitor = getAnonymousVisitorId(req);
    let discoveryAttribution:
        | DiscoveryTicketAttribution
        | typeof NO_DISCOVERY_TICKET_ATTRIBUTION =
        NO_DISCOVERY_TICKET_ATTRIBUTION;
    if (impressionId) {
        try {
            discoveryAttribution =
                (await resolveDiscoveryTicketAttribution({
                    impressionId,
                    showId,
                    profileId,
                    anonymousVisitorId:
                        req.cookies.get(ANON_COOKIE)?.value ?? null,
                })) ?? NO_DISCOVERY_TICKET_ATTRIBUTION;
        } catch (error) {
            console.error(
                "GET /api/v1/tickets/out discovery attribution lookup failed:",
                error,
            );
        }
    }

    await db.ticketPurchaseClickEvent.create({
        data: {
            showId,
            clubId: show.clubId,
            profileId,
            anonymousVisitorId: anonymousVisitor.id,
            destinationUrl: destination.originalUrl,
            routedDestinationUrl: destination.routedUrl,
            destinationProvider: destination.provider,
            affiliateApplied: destination.affiliateApplied,
            fallbackReason: destination.fallbackReason,
            sourceSurface,
            userAgent: req.headers.get("user-agent"),
            deviceMetadata: {
                outboundRoute: true,
            } satisfies Prisma.JsonObject,
            ...discoveryAttribution,
        },
    });

    const response = NextResponse.redirect(destination.routedUrl, {
        status: 302,
        headers: rateLimitHeaders(rl),
    });
    if (anonymousVisitor.shouldSetCookie) {
        response.cookies.set(ANON_COOKIE, anonymousVisitor.id, {
            httpOnly: true,
            sameSite: "lax",
            secure: process.env.NODE_ENV === "production",
            path: "/",
            maxAge: ANON_COOKIE_MAX_AGE_SECONDS,
        });
    }
    return response;
});
