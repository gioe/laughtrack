import { TicketClickSourceSurface } from "@/util/ticketClickTracking";

interface BuildTicketOutboundHrefInput {
    showId: number;
    clubId: number;
    destinationUrl: string;
    sourceSurface: TicketClickSourceSurface;
}

export function buildTicketOutboundHref({
    showId,
    clubId,
    destinationUrl,
    sourceSurface,
}: BuildTicketOutboundHrefInput): string {
    const params = new URLSearchParams({
        showId: String(showId),
        clubId: String(clubId),
        surface: sourceSurface,
        url: destinationUrl,
    });
    return `/api/v1/tickets/out?${params.toString()}`;
}
