import { NextRequest, NextResponse } from "next/server";
import { NotFoundError } from "@/objects/NotFoundError";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { findRelatedShowsForShow } from "@/lib/data/show/detail/findRelatedShowsForShow";
import { findShowById } from "@/lib/data/show/detail/findShowById";
import { TicketDTO } from "@/objects/class/ticket/ticket.interface";

const POSITIVE_INTEGER_RE = /^[1-9]\d*$/;

function parseShowId(raw: string): number | null {
    if (!POSITIVE_INTEGER_RE.test(raw)) return null;

    const numericId = Number(raw);
    if (!Number.isSafeInteger(numericId)) return null;

    return numericId;
}

function pickCtaUrl(
    tickets: TicketDTO[] | undefined,
    showPageUrl: string,
): string | null {
    const liveTicket = tickets?.find(
        (ticket) => !ticket.soldOut && ticket.purchaseUrl,
    );
    if (liveTicket?.purchaseUrl) return liveTicket.purchaseUrl;
    return showPageUrl || null;
}

function buildCtaLabel(showName: string | null, clubName?: string): string {
    if (showName?.trim()) {
        return `Get tickets for ${showName}`;
    }

    return `Get tickets for comedy show at ${clubName ?? "this venue"}`;
}

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "shows-id");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = parseShowId(id);

    if (numericId === null) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const { show, clubId } = await findShowById(numericId);
        const relatedShows = await findRelatedShowsForShow(numericId, clubId);
        const ctaUrl = pickCtaUrl(show.tickets, show.showPageUrl);
        const explicitlySoldOut =
            show.tickets !== undefined &&
            show.tickets.length > 0 &&
            show.tickets.every((ticket) => ticket.soldOut);

        return NextResponse.json(
            {
                data: {
                    ...show,
                    club: {
                        id: clubId,
                        name: show.clubName ?? null,
                        address: show.address ?? null,
                        imageUrl: show.imageUrl,
                        timezone: show.timezone ?? null,
                    },
                    cta: {
                        url: ctaUrl,
                        label: buildCtaLabel(show.name, show.clubName),
                        isSoldOut: explicitlySoldOut || !ctaUrl,
                    },
                },
                relatedShows,
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        if (error instanceof NotFoundError) {
            return NextResponse.json(
                { error: "Show not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        console.error("GET /api/v1/shows/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch show" },
            { status: 500 },
        );
    }
}
