import { NextRequest, NextResponse } from "next/server";
import { findShowDensity } from "@/lib/data/show/search/findShowDensity";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { SearchParams } from "@/objects/interface";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DEFAULT_DISTANCE = "25";
const MAX_RANGE_DAYS = 90;

function parseIsoDate(value: string): Date | null {
    if (!ISO_DATE_RE.test(value)) return null;

    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (
        date.getUTCFullYear() !== year ||
        date.getUTCMonth() !== month - 1 ||
        date.getUTCDate() !== day
    ) {
        return null;
    }
    return date;
}

function formatIsoDate(date: Date): string {
    return date.toISOString().slice(0, 10);
}

function addUtcDays(date: Date, days: number): Date {
    const copy = new Date(date);
    copy.setUTCDate(copy.getUTCDate() + days);
    return copy;
}

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "shows-density");
    if (rl instanceof NextResponse) return rl;

    const sp = req.nextUrl.searchParams;
    const zip = sp.get("zip") ?? undefined;
    const fromRaw = sp.get("from");
    const toRaw = sp.get("to");
    const distance = sp.get("distance");
    const comedian = sp.get("comedian") ?? undefined;
    const club = sp.get("club") ?? undefined;

    if (comedian !== undefined && club !== undefined) {
        return NextResponse.json(
            { error: "comedian and club are mutually exclusive" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const today = new Date();
    const fromDate = fromRaw
        ? parseIsoDate(fromRaw)
        : parseIsoDate(formatIsoDate(today));
    if (!fromDate) {
        return NextResponse.json(
            { error: "from must be a valid date in YYYY-MM-DD format" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const requestedToDate = toRaw
        ? parseIsoDate(toRaw)
        : addUtcDays(fromDate, MAX_RANGE_DAYS - 1);
    if (!requestedToDate) {
        return NextResponse.json(
            { error: "to must be a valid date in YYYY-MM-DD format" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    if (requestedToDate < fromDate) {
        return NextResponse.json(
            { error: "to must be on or after from" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (zip !== undefined && !/^\d{5}$/.test(zip)) {
        return NextResponse.json(
            { error: "zip must be a 5-digit US zip code" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    if (distance !== null) {
        const distanceNum = Number(distance);
        if (isNaN(distanceNum) || distanceNum < 1 || distanceNum > 500) {
            return NextResponse.json(
                { error: "distance must be a number between 1 and 500 miles" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
    }

    const tzResult = readTimezoneHeader(req);
    if (!tzResult.ok) {
        return NextResponse.json(
            { error: tzResult.error },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const cappedToDate =
        requestedToDate > addUtcDays(fromDate, MAX_RANGE_DAYS - 1)
            ? addUtcDays(fromDate, MAX_RANGE_DAYS - 1)
            : requestedToDate;

    const params: SearchParams = {
        fromDate: formatIsoDate(fromDate),
        toDate: formatIsoDate(cappedToDate),
        zip,
        distance: zip ? (distance ?? DEFAULT_DISTANCE) : undefined,
        comedian,
        club,
    };

    try {
        const density = await findShowDensity(
            new QueryHelper({ params, timezone: tzResult.timezone }),
        );

        return NextResponse.json(density, { headers: rateLimitHeaders(rl) });
    } catch (error) {
        console.error("GET /api/v1/shows/density error:", error);
        return NextResponse.json(
            { error: "Failed to fetch show density" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
