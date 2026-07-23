"use client";

import Link from "next/link";
import {
    ArrowUpRight,
    Building2,
    Calendar,
    Ticket as TicketIcon,
} from "lucide-react";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";
import {
    formatTicketString,
    hasUnknownAvailableTicketPrice,
} from "@/util/ticket/ticketUtil";
import { formatShowDate } from "@/util/dateUtil";
import { Ticket } from "@/objects/class/ticket/Ticket";
import { TicketDTO } from "@/objects/class/ticket/ticket.interface";
import PriceUnavailableInfo from "@/ui/components/tickets/PriceUnavailableInfo";
import { buildTicketOutboundHref } from "@/util/ticketOutboundLink";
import { TicketStub, TicketStubRow } from "@/ui/components/ticketStub";

interface ShowTicketCtaProps {
    show: ShowDetailDTO;
    isPast: boolean;
    isOpenMic?: boolean;
    discoveryImpressionId?: string;
}

// Picks the best external URL: a live ticket row, else the scraped show page.
function pickTicketUrl(show: ShowDetailDTO): string | null {
    const tickets = show.tickets ?? [];
    const live = tickets.find((t: TicketDTO) => !t.soldOut && t.purchaseUrl);
    if (live?.purchaseUrl) return live.purchaseUrl;
    return show.showPageUrl || null;
}

const ShowTicketCta: React.FC<ShowTicketCtaProps> = ({
    show,
    isPast,
    isOpenMic = false,
    discoveryImpressionId,
}) => {
    const url = pickTicketUrl(show);
    const tickets = (show.tickets ?? []).map((t) => new Ticket(t));
    const liveTickets = tickets.filter((t) => !t.soldOut);
    // Open-mic shows are free / pay-what-you-can; suppress price and any
    // "price unavailable" affordance so the CTA reads as an RSVP, not a sale.
    const priceLabel = isOpenMic ? null : formatTicketString(liveTickets);
    const hasUnknownPrice =
        !isOpenMic && hasUnknownAvailableTicketPrice(show.tickets ?? []);
    const explicitlySoldOut =
        show.soldOut === true ||
        (tickets.length > 0 && tickets.every((t) => t.soldOut));

    // Sold Out only when tickets exist and every row says soldOut, OR when we
    // have no URL at all to send the user to. Zero ticket rows + a valid
    // showPageUrl still routes users to the venue. Ended takes precedence.
    const isSoldOut = !isPast && (explicitlySoldOut || !url);
    const isLive = !isPast && !isSoldOut && !!url;

    const dateLabel = formatShowDate(show.date.toString(), show.timezone);
    // Some scrapers write the club name into room (e.g. show 1779237), which
    // would repeat the club-name value rendered directly above this sub-line.
    const room =
        show.room &&
        show.room.trim().toLowerCase() === show.clubName?.trim().toLowerCase()
            ? null
            : show.room;
    const venueDetail = [room, show.address].filter(Boolean).join(" · ");

    let ticketsValue: React.ReactNode;
    if (isPast) {
        ticketsValue = "This show has ended.";
    } else if (isSoldOut) {
        ticketsValue = <span className="text-red-700">Sold Out</span>;
    } else if (isOpenMic) {
        ticketsValue = "RSVP";
    } else {
        // Mirrors iOS detailTicketSummary: price range when known, otherwise
        // "Price unavailable" with the info affordance explaining why.
        ticketsValue = (
            <span className="flex items-center gap-2">
                {priceLabel || "Price unavailable"}
                {hasUnknownPrice && <PriceUnavailableInfo />}
            </span>
        );
    }

    let buyPill: React.ReactNode = null;
    if (isLive && url) {
        const ctaCopy = isOpenMic ? "RSVP" : "Buy tickets";
        const ctaLabel = isOpenMic
            ? show.name
                ? `RSVP for ${show.name}`
                : `RSVP for open mic at ${show.clubName ?? "this venue"}`
            : show.name
              ? `Buy tickets for ${show.name}`
              : `Buy tickets for comedy show at ${show.clubName ?? "this venue"}`;
        const outboundHref = buildTicketOutboundHref({
            showId: show.id,
            clubId: show.clubId,
            destinationUrl: url,
            sourceSurface: "show_detail",
            impressionId: discoveryImpressionId,
        });
        buyPill = (
            <a
                href={outboundHref}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={ctaLabel}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-copper px-3.5 py-2 font-dmSans text-caption font-bold uppercase tracking-wider text-white shadow-md shadow-copper/40 transition hover:bg-copper-bright focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                {ctaCopy}
                <ArrowUpRight size={12} strokeWidth={3} aria-hidden="true" />
            </a>
        );
    }

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-8 mb-10">
            <div className="max-w-md">
                <TicketStub
                    stub={
                        <TicketStubRow
                            icon={<TicketIcon size={16} />}
                            label="Tickets"
                            value={ticketsValue}
                            trailing={buyPill}
                        />
                    }
                >
                    <TicketStubRow
                        icon={<Calendar size={16} />}
                        label="When"
                        value={dateLabel}
                    />
                    {(show.clubName || venueDetail) && (
                        <TicketStubRow
                            icon={<Building2 size={16} />}
                            label="Venue"
                            value={
                                <>
                                    {show.clubName ? (
                                        <Link
                                            href={`/club/${show.clubName}`}
                                            className="underline-offset-2 hover:underline focus-visible:underline"
                                        >
                                            {show.clubName}
                                        </Link>
                                    ) : (
                                        "This venue"
                                    )}
                                    {venueDetail && (
                                        <p className="font-dmSans text-xs font-normal text-copper-dark/80">
                                            {venueDetail}
                                        </p>
                                    )}
                                </>
                            }
                        />
                    )}
                </TicketStub>
                {isLive && (
                    <p className="mt-2 text-xs text-muted-foreground font-dmSans">
                        Opens the venue&apos;s{" "}
                        {isOpenMic ? "signup" : "ticketing"} page in a new tab.
                    </p>
                )}
            </div>
        </section>
    );
};

export default ShowTicketCta;
