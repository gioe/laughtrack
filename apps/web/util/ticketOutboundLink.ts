import { TicketClickSourceSurface } from "@/util/ticketClickTracking";

interface BuildTicketOutboundHrefInput {
    showId: number;
    clubId: number;
    destinationUrl: string;
    sourceSurface: TicketClickSourceSurface;
    impressionId?: string;
}

export function buildTicketOutboundHref({
    showId,
    clubId,
    destinationUrl,
    sourceSurface,
    impressionId,
}: BuildTicketOutboundHrefInput): string {
    const params = new URLSearchParams({
        showId: String(showId),
        clubId: String(clubId),
        surface: sourceSurface,
        url: destinationUrl,
    });
    if (impressionId) params.set("impressionId", impressionId);
    return `/api/v1/tickets/out?${params.toString()}`;
}
