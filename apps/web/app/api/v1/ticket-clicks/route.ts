import { db } from "@/lib/db";
import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import {
    RATE_LIMITS,
    checkRateLimit,
    getClientIp,
    rateLimitHeaders,
    rateLimitResponse,
} from "@/lib/rateLimit";
import { Prisma } from "@prisma/client";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";

const ANON_COOKIE = "lt_anon_visitor_id";
const ANON_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 395;
const SOURCE_SURFACES = new Set([
    "show_detail",
    "show_card",
    "compact_show_card",
    "ios_show_detail",
]);

function parsePositiveInt(value: unknown): number | null {
    if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
        return null;
    }
    return Number.isSafeInteger(value) ? value : null;
}

function parseDestinationUrl(value: unknown): string | null {
    if (typeof value !== "string" || value.length > 2048) return null;
    try {
        const url = new URL(value);
        return url.protocol === "http:" || url.protocol === "https:"
            ? url.toString()
            : null;
    } catch {
        return null;
    }
}

function parseDeviceMetadata(value: unknown): Prisma.JsonObject {
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return value as Prisma.JsonObject;
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

export async function POST(req: NextRequest) {
    let payload: unknown;
    try {
        payload = await req.json();
    } catch {
        return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }

    const data = payload as Record<string, unknown>;
    const showId = parsePositiveInt(data.showId);
    const clientClubId = parsePositiveInt(data.clubId);
    const destinationUrl = parseDestinationUrl(data.destinationUrl);
    const sourceSurface =
        typeof data.sourceSurface === "string" &&
        SOURCE_SURFACES.has(data.sourceSurface)
            ? data.sourceSurface
            : null;

    if (!showId || !clientClubId || !destinationUrl || !sourceSurface) {
        return NextResponse.json(
            { error: "Invalid ticket click payload" },
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
    if (show.clubId !== clientClubId) {
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
            destinationUrl,
            sourceSurface,
            userAgent: req.headers.get("user-agent"),
            deviceMetadata: parseDeviceMetadata(data.deviceMetadata),
        },
    });

    const response = NextResponse.json(
        { ok: true },
        { status: 201, headers: rateLimitHeaders(rl) },
    );
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
}

function parseDateParam(value: string | null): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function toNumber(value: bigint | number | string | null | undefined): number {
    return Number(value ?? 0);
}

export async function GET(req: NextRequest) {
    const admin = await requireAdminForApi();
    if (!admin.ok) return admin.response;

    const { searchParams } = new URL(req.url);
    const from = parseDateParam(searchParams.get("from"));
    const to = parseDateParam(searchParams.get("to"));
    const showId = searchParams.get("showId")
        ? Number(searchParams.get("showId"))
        : null;
    const clubId = searchParams.get("clubId")
        ? Number(searchParams.get("clubId"))
        : null;

    if (
        (searchParams.get("from") && !from) ||
        (searchParams.get("to") && !to) ||
        (showId !== null && (!Number.isInteger(showId) || showId <= 0)) ||
        (clubId !== null && (!Number.isInteger(clubId) || clubId <= 0))
    ) {
        return NextResponse.json(
            { error: "Invalid reporting filters" },
            { status: 400 },
        );
    }

    const filters: Prisma.Sql[] = [];
    if (from) filters.push(Prisma.sql`created_at >= ${from}`);
    if (to) filters.push(Prisma.sql`created_at <= ${to}`);
    if (showId) filters.push(Prisma.sql`show_id = ${showId}`);
    if (clubId) filters.push(Prisma.sql`club_id = ${clubId}`);

    const where =
        filters.length > 0
            ? Prisma.sql`WHERE ${Prisma.join(filters, " AND ")}`
            : Prisma.empty;

    const rows = await db.$queryRaw<
        Array<{
            total_clicks: bigint;
            unique_signed_in_users: bigint;
            unique_anonymous_visitors: bigint;
        }>
    >`
        SELECT
            COUNT(*)::bigint AS total_clicks,
            COUNT(DISTINCT profile_id)::bigint AS unique_signed_in_users,
            COUNT(DISTINCT CASE WHEN profile_id IS NULL THEN anonymous_visitor_id END)::bigint AS unique_anonymous_visitors
        FROM ticket_purchase_click_events
        ${where}
    `;
    const row = rows[0];

    return NextResponse.json({
        totalClicks: toNumber(row?.total_clicks),
        uniqueSignedInUsers: toNumber(row?.unique_signed_in_users),
        uniqueAnonymousVisitors: toNumber(row?.unique_anonymous_visitors),
    });
}
