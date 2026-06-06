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
    resolveAffiliateDestination,
} from "@/lib/affiliate/affiliateRouting";
import { Prisma } from "@prisma/client";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";

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
        select: { id: true, clubId: true },
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

    const authCtx = await resolveAuth(req);
    const profileId =
        authCtx && authCtx !== PROFILE_MISSING ? authCtx.profileId : null;
    const rl = await applyTicketClickRateLimit(req, profileId);
    if (rl instanceof NextResponse) return rl;

    const anonymousVisitor = getAnonymousVisitorId(req);
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
        } as any,
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
