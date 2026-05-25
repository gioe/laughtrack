"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Show } from "@/objects/class/show/Show";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { formatShowDate } from "@/util/dateUtil";
import {
    formatTicketString,
    hasUnknownAvailableTicketPrice,
} from "@/util/ticket/ticketUtil";
import EntityCard from "../../entity";
import PriceUnavailableInfo from "@/ui/components/tickets/PriceUnavailableInfo";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

// Subtle warm spotlight wash from the top edge — the compact echo of the
// show-search card's Brick & Spotlight stage treatment.
const CARD_SPOTLIGHT =
    "radial-gradient(85% 65% at 50% -12%, rgba(247,231,206,0.10), rgba(184,115,51,0.04) 45%, transparent 70%)";

interface CompactShowCardProps {
    show: ShowDTO;
}

const CompactShowCard: React.FC<CompactShowCardProps> = ({ show }) => {
    const [imgError, setImgError] = useState(false);
    const parsedShow = new Show(show);

    const availableTickets = parsedShow.tickets.filter((t) => !t.soldOut);
    const ticketLabel = formatTicketString(availableTickets);
    const buyUrl =
        availableTickets.length > 0
            ? availableTickets[0].purchaseUrl
            : undefined;
    const isSoldOut =
        parsedShow.soldOut === true ||
        (parsedShow.tickets.length > 0 && availableTickets.length === 0);
    const struckPriceLabel =
        isSoldOut && parsedShow.tickets.length > 0
            ? formatTicketString(parsedShow.tickets)
            : "";

    const lineupNames = parsedShow.lineup.map((c) => c.name).filter(Boolean);
    const displayNames = lineupNames.slice(0, 2).join(", ");
    const extraCount = lineupNames.length - 2;

    const detailHref = `/show/${show.id}`;
    const showDescriptor = parsedShow.name
        ? parsedShow.name
        : `show at ${parsedShow.clubName ?? "comedy club"}`;
    const detailLabel = `View details for ${showDescriptor}`;
    const ticketAriaLabel = buyUrl
        ? `Get tickets for ${showDescriptor}`
        : undefined;
    const hasUnknownPrice = hasUnknownAvailableTicketPrice(parsedShow.tickets);

    return (
        <EntityCard
            as="article"
            chrome="stage"
            className="relative h-full overflow-hidden p-4"
        >
            {/* Warm spotlight wash behind the content (content sits in the
                relative wrapper below so it paints above this layer). */}
            <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0"
                style={{ background: CARD_SPOTLIGHT }}
            />

            {/* Stretched-link overlay: whole card navigates to /show/[id].
                The ticket link below uses `relative z-[2]` so it still opens
                the external ticketing URL in a new tab. */}
            <Link
                href={detailHref}
                aria-label={detailLabel}
                className="absolute inset-0 z-[1] rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                <span className="sr-only">View show details</span>
            </Link>

            <div className="relative flex h-full flex-col gap-3">
                {/* Club header */}
                <div className="flex items-center gap-3">
                    <div
                        className={`relative h-10 w-10 flex-none overflow-hidden rounded-full bg-[#241912] ring-1 ring-copper/25 ${isSoldOut ? "grayscale opacity-60" : ""}`}
                    >
                        <Image
                            src={imgError ? PLACEHOLDER : parsedShow.imageUrl}
                            onError={() => setImgError(true)}
                            alt={parsedShow.clubName ?? "Club"}
                            fill
                            className="object-cover"
                            sizes="40px"
                            aria-hidden="true"
                        />
                    </div>
                    <div className="min-w-0">
                        <p
                            data-testid="compact-show-title"
                            className="font-gilroy-bold font-bold text-foreground text-body leading-tight line-clamp-2"
                        >
                            {parsedShow.name || "Untitled show"}
                        </p>
                        {parsedShow.clubName && (
                            <p
                                data-testid="compact-show-club"
                                className="font-oswald text-[11px] font-medium uppercase tracking-[0.08em] text-copper-bright leading-snug line-clamp-2"
                            >
                                {parsedShow.clubName}
                            </p>
                        )}
                        {parsedShow.room && (
                            <p className="text-[11px] text-foreground/50 font-dmSans truncate">
                                {parsedShow.room}
                            </p>
                        )}
                    </div>
                </div>

                {/* Date & address */}
                <div className="text-caption text-foreground/65 font-dmSans space-y-0.5">
                    <p>
                        {formatShowDate(
                            parsedShow.date.toString(),
                            parsedShow.timezone,
                        )}
                    </p>
                    {parsedShow.address && (
                        <p className="truncate">{parsedShow.address}</p>
                    )}
                </div>

                {/* Lineup */}
                {lineupNames.length > 0 && (
                    <p className="text-caption text-foreground/70 font-dmSans">
                        w/ {displayNames}
                        {extraCount > 0 && ` +${extraCount} more`}
                    </p>
                )}

                {/* Ticket CTA */}
                {parsedShow.tickets.length > 0 && (
                    <div className="mt-auto pt-1 relative z-[2]">
                        {buyUrl ? (
                            <div className="flex flex-wrap items-center gap-2">
                                <Link
                                    href={buyUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={ticketAriaLabel}
                                    className="inline-block text-caption font-semibold text-copper-bright font-dmSans hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                >
                                    {ticketLabel || "Get Tickets"}
                                </Link>
                                {hasUnknownPrice && (
                                    <PriceUnavailableInfo className="h-7 w-7" />
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center gap-2">
                                {struckPriceLabel && (
                                    <span className="text-caption text-foreground/45 line-through font-dmSans">
                                        {struckPriceLabel}
                                    </span>
                                )}
                                <span className="inline-block text-caption font-bold text-white bg-red-500 px-2.5 py-0.5 rounded-full font-dmSans">
                                    Sold Out
                                </span>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </EntityCard>
    );
};

export default CompactShowCard;
