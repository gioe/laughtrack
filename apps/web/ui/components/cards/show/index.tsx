"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { MapPin, Mic } from "lucide-react";
import { Button } from "@/ui/components/ui/button";
import { Show } from "@/objects/class/show/Show";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";
import EntityCard from "../entity";
import { formatShowDate } from "@/util/dateUtil";
import {
    formatTicketString,
    hasUnknownAvailableTicketPrice,
} from "@/util/ticket/ticketUtil";
import PriceUnavailableInfo from "@/ui/components/tickets/PriceUnavailableInfo";
import { buildTicketOutboundHref } from "@/util/ticketOutboundLink";
import { cn } from "@/util/tailwindUtil";

// NOTE: Responsive classes in this file use project-custom Tailwind breakpoints
// (not Tailwind defaults). See tailwind.config.ts `theme.screens` for definitions:
//   xs  → max-width  575px  (mobile portrait)
//   sm  → 576–897px         (mobile landscape)
//   md  → 898–1199px        (tablet)
//   lg  → min-width 1200px  (desktop)
// Module-level Set that persists for the lifetime of the JS module (i.e., the browser session tab).
// Purpose: suppress entry animations when a ShowCard remounts for a show the user has already seen
// this session (e.g., navigating away and returning to the same search results).
//
// Trade-off: first-visit cards animate in; return-visit cards skip the animation.
// This is intentional — re-animating already-seen cards on back-navigation is jarring.
// Framer's `viewport={{ once: true }}` only suppresses within one component lifecycle;
// this Set extends that guarantee across remounts.
//
// An alternative (per-route context) was evaluated and ruled out: the added complexity
// is not justified for this UX improvement given that the suppress-on-return behavior
// is acceptable and consistent with common list animation patterns.
const seenShowIds = new Set<number>();
const CLUB_PLACEHOLDER = "/placeholders/club-placeholder.svg";

// Faint exposed-brick texture for the card surface — two repeating-line layers
// at low alpha read as masonry without competing with the content.
const BRICK_TEXTURE =
    "repeating-linear-gradient(0deg, rgba(255,255,255,0.045) 0px, rgba(255,255,255,0.045) 1px, transparent 1px, transparent 22px)," +
    "repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 46px)";

// Warm spotlight wash falling across the card from the upper-right (toward the
// visual panel), so the whole card reads as a lit stage rather than a flat box.
const CARD_SPOTLIGHT =
    "radial-gradient(62% 70% at 80% -10%, rgba(247,231,206,0.12), rgba(184,115,51,0.05) 42%, transparent 72%)";

// Subtle warm spotlight wash from the top edge — the compact echo of the
// standard density's Brick & Spotlight stage treatment.
const COMPACT_CARD_SPOTLIGHT =
    "radial-gradient(85% 65% at 50% -12%, rgba(247,231,206,0.10), rgba(184,115,51,0.04) 45%, transparent 70%)";

// Backdrop for the visual panel: a single spotlight cone from above + a copper
// floor pool below over a warm near-black, evoking a comedy-club stage.
const STAGE_BACKDROP =
    "radial-gradient(120% 82% at 50% -14%, rgba(247,231,206,0.20), rgba(247,231,206,0.05) 38%, transparent 66%)," +
    "radial-gradient(72% 36% at 50% 106%, rgba(184,115,51,0.18), transparent 70%)," +
    "linear-gradient(180deg, #1c140e 0%, #100b08 100%)";

export type ShowCardContext = "default" | "comedian-detail";
export type ShowCardDensity = "standard" | "compact";

interface ShowCardProps {
    show: ShowDTO;
    /**
     * "standard" — full-width stage card with the brick + spotlight chrome
     * (search results, favorites, past shows). "compact" — narrow card for
     * rails and dense grids. Mirrors iOS LaughTrackCardDensity.
     */
    density?: ShowCardDensity;
    /** Standard density only. */
    hideClubName?: boolean;
    /** Standard density only. */
    variant?: "default" | "past";
    /** Standard density only. */
    context?: ShowCardContext;
}

// Density dispatch happens across separate internal components so each
// density keeps an unconditional hook set.
const ShowCard: React.FC<ShowCardProps> = ({
    show,
    density = "standard",
    hideClubName,
    variant = "default",
    context = "default",
}: ShowCardProps) => {
    if (density === "compact") {
        return <CompactShowCard show={show} />;
    }
    return (
        <StandardShowCard
            show={show}
            hideClubName={hideClubName}
            variant={variant}
            context={context}
        />
    );
};

interface StandardShowCardProps {
    show: ShowDTO;
    hideClubName?: boolean;
    variant: "default" | "past";
    context: ShowCardContext;
}

const StandardShowCard: React.FC<StandardShowCardProps> = ({
    show,
    hideClubName,
    variant,
    context,
}: StandardShowCardProps) => {
    const distanceMiles = show.distanceMiles ?? null;
    const parsedShow = new Show(show);
    const isPast = variant === "past";
    const isSoldOut = parsedShow.soldOut === true;
    const stillOnSale =
        !isSoldOut &&
        parsedShow.tickets.filter((ticket) => !ticket.soldOut).length > 0;
    // Read before useEffect so first render always animates, remounts skip it
    const alreadySeen = seenShowIds.has(show.id);

    useEffect(() => {
        seenShowIds.add(show.id);
    }, [show.id]);

    const detailHref = `/show/${show.id}`;
    const showDescriptor = parsedShow.name
        ? parsedShow.name
        : `show at ${parsedShow.clubName ?? "comedy club"}`;
    const detailLabel = `View details for ${showDescriptor}`;
    const ticketLabel = stillOnSale
        ? `Get tickets for ${showDescriptor}`
        : `${showDescriptor} is sold out`;
    const renderVisualPanel = () => {
        if (context === "comedian-detail" || parsedShow.lineup.length === 0) {
            return <ShowCardArtwork show={parsedShow} />;
        }
        return (
            <div
                className="relative overflow-hidden rounded-lg border border-copper/15 px-4 pt-3 pb-1 shadow-inner sm:px-5 sm:pt-4"
                style={{ background: STAGE_BACKDROP }}
            >
                <div className="mb-2 flex items-center gap-2">
                    <Mic
                        size={13}
                        aria-hidden="true"
                        className="text-copper-bright"
                    />
                    <span className="font-oswald text-[11px] font-medium uppercase tracking-[0.22em] text-copper-bright">
                        Lineup
                    </span>
                    <span className="h-px flex-1 bg-copper/20" />
                </div>
                <LineupGrid lineup={parsedShow.lineup} />
            </div>
        );
    };

    return (
        <EntityCard
            as="article"
            chrome="stage"
            className={
                isPast
                    ? "relative p-4 sm:p-6 overflow-hidden w-full shadow-sm hover:shadow-md border-copper/10 bg-[#141009] opacity-90"
                    : "relative p-4 sm:p-6 overflow-hidden w-full hover:shadow-xl hover:shadow-black/50"
            }
            animateEntryY={isPast ? undefined : 20}
            alreadySeen={alreadySeen}
        >
            {/* Decorative club-wall atmosphere: faint brick masonry + a warm
                spotlight wash. Sits behind all content (first in DOM, no z-index)
                and ignores pointer events so the stretched link still works. */}
            <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl"
            >
                <div
                    className={
                        isPast
                            ? "absolute inset-0 opacity-[0.025]"
                            : "absolute inset-0 opacity-[0.05]"
                    }
                    style={{ backgroundImage: BRICK_TEXTURE }}
                />
                <div
                    className={
                        isPast
                            ? "absolute inset-0 opacity-40"
                            : "absolute inset-0"
                    }
                    style={{ background: CARD_SPOTLIGHT }}
                />
            </div>

            {/* Stretched-link overlay: whole card navigates to the internal show detail.
                Inner interactive elements (ticket button, lineup headshots) sit on top
                via `relative z-[2]` so their clicks aren't swallowed. */}
            <Link
                href={detailHref}
                aria-label={detailLabel}
                className="absolute inset-0 z-[1] rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                <span className="sr-only">View show details</span>
            </Link>

            <div className="relative flex flex-col lg:flex-row gap-4">
                <div className="flex-1 lg:w-[35%] flex flex-col gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="flex-1">
                            <ShowCardHeader
                                show={parsedShow}
                                distanceMiles={distanceMiles}
                                hideClubName={hideClubName}
                                variant={variant}
                            />
                        </div>

                        {isPast ? (
                            <p className="sm:self-start relative z-[2] rounded-full border border-copper/15 bg-black/30 px-3 py-1.5 text-sm font-dmSans text-foreground/60">
                                Performed on{" "}
                                {formatShowDate(
                                    parsedShow.date.toString(),
                                    parsedShow.timezone,
                                )}
                            </p>
                        ) : (
                            parsedShow.tickets.length > 0 &&
                            (() => {
                                const purchaseUrl =
                                    parsedShow.tickets[0].purchaseUrl;
                                const canPurchase =
                                    stillOnSale && !!purchaseUrl;
                                const outboundHref = purchaseUrl
                                    ? buildTicketOutboundHref({
                                          showId: show.id,
                                          clubId: show.clubId,
                                          destinationUrl: purchaseUrl,
                                          sourceSurface: "show_card",
                                      })
                                    : "";
                                const hasUnknownPrice =
                                    hasUnknownAvailableTicketPrice(
                                        parsedShow.tickets,
                                    );
                                return (
                                    <div className="sm:self-start relative z-[2] flex flex-wrap items-center gap-2">
                                        {canPurchase ? (
                                            <Button
                                                asChild
                                                variant="roundedShimmer"
                                            >
                                                <a
                                                    href={outboundHref}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    aria-label={ticketLabel}
                                                >
                                                    Get Tickets
                                                </a>
                                            </Button>
                                        ) : (
                                            <Button
                                                type="button"
                                                variant="roundedShimmer"
                                                className={
                                                    stillOnSale
                                                        ? undefined
                                                        : "bg-red-500"
                                                }
                                                disabled={!stillOnSale}
                                                aria-label={ticketLabel}
                                            >
                                                {stillOnSale
                                                    ? "Get Tickets"
                                                    : "Sold Out"}
                                            </Button>
                                        )}
                                        {hasUnknownPrice && (
                                            <PriceUnavailableInfo />
                                        )}
                                    </div>
                                );
                            })()
                        )}
                    </div>

                    <div className="lg:hidden relative z-[2]">
                        <Divider />
                        <div className="pt-2 sm:pt-4">
                            {renderVisualPanel()}
                        </div>
                    </div>
                </div>

                <div className="hidden lg:block lg:w-[65%] relative z-[2]">
                    {renderVisualPanel()}
                </div>
            </div>
        </EntityCard>
    );
};

interface ShowCardHeaderProps {
    show: Show;
    distanceMiles?: number | null;
    hideClubName?: boolean;
    variant?: "default" | "past";
}

const ShowCardHeader: React.FC<ShowCardHeaderProps> = ({
    show,
    distanceMiles,
    hideClubName,
    variant = "default",
}: ShowCardHeaderProps) => {
    const [error, setError] = useState(false);
    const isPast = variant === "past";
    const isSoldOut = show.soldOut === true;

    return (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div
                className={cn(
                    "relative aspect-square w-[12%] min-w-[48px] max-w-[64px] rounded-full overflow-hidden bg-[#241912] ring-1 ring-copper/25",
                    isSoldOut && "grayscale opacity-60",
                )}
            >
                <Image
                    src={error ? CLUB_PLACEHOLDER : show.imageUrl}
                    onError={() => setError(true)}
                    alt={show.clubName ?? "Club logo"}
                    fill
                    className="object-cover"
                    sizes="(max-width: 48px) 48px, 64px"
                />
            </div>

            <div>
                {show.name ? (
                    <h3
                        className={cn(
                            "text-xl sm:text-2xl md:text-h3 font-urbanist-bold text-foreground mb-1",
                            isPast ? "font-semibold" : "font-bold",
                        )}
                    >
                        {show.name}
                    </h3>
                ) : (
                    <h3
                        className={cn(
                            "text-xl sm:text-2xl md:text-h3 font-urbanist-bold text-foreground mb-1",
                            isPast && "font-normal",
                        )}
                    >
                        Untitled show
                    </h3>
                )}
                {!hideClubName && show.clubName && (
                    <p className="text-base font-oswald font-medium uppercase tracking-[0.14em] text-foreground/85 mb-1">
                        {show.clubName}
                    </p>
                )}
                {show.room && (
                    <p className="text-sm text-foreground/55 font-dmSans mb-1">
                        {show.room}
                    </p>
                )}
                <p className="text-base sm:text-lg md:text-lead text-foreground/65 font-dmSans">
                    {formatShowDate(show.date.toString(), show.timezone)} ·{" "}
                    {`${show.address}`}
                </p>
                {distanceMiles != null && (
                    <p className="flex items-center gap-1 text-sm text-copper-bright font-dmSans mt-0.5">
                        <MapPin size={13} aria-hidden="true" />
                        {distanceMiles < 1
                            ? "< 1 mile away"
                            : `${Math.round(distanceMiles)} miles away`}
                    </p>
                )}
                {!isPast && !isSoldOut && (
                    <p className="text-lg sm:text-xl md:text-lead text-copper-bright font-semibold mt-1 font-dmSans">
                        {formatTicketString(
                            show.tickets.filter((ticket) => !ticket.soldOut),
                        )}
                    </p>
                )}
                {!isPast && isSoldOut && formatTicketString(show.tickets) && (
                    <p className="text-lg sm:text-xl md:text-lead text-foreground/45 line-through font-semibold mt-1 font-dmSans">
                        {formatTicketString(show.tickets)}
                    </p>
                )}
            </div>
        </div>
    );
};

const ShowCardArtwork = ({ show }: { show: Show }) => {
    const [imageError, setImageError] = useState(false);
    const hasArtwork = !!show.imageUrl && show.imageUrl !== CLUB_PLACEHOLDER;
    const showImage = hasArtwork && !imageError;
    const formattedDate = formatShowDate(show.date.toString(), show.timezone);
    const altText = show.clubName
        ? `${show.clubName} venue artwork`
        : "Comedy venue artwork";
    const isSoldOut = show.soldOut === true;

    return (
        <div
            className={`pointer-events-none relative min-h-[176px] overflow-hidden rounded-lg border border-copper/15 shadow-inner sm:min-h-[220px] lg:min-h-[248px] ${isSoldOut ? "grayscale opacity-70" : ""}`}
            style={showImage ? undefined : { background: STAGE_BACKDROP }}
        >
            {showImage ? (
                <Image
                    src={show.imageUrl}
                    onError={() => setImageError(true)}
                    alt={altText}
                    fill
                    className="object-contain"
                    sizes="(max-width: 1199px) 100vw, 65vw"
                />
            ) : (
                // No artwork: a lone mic caught in the spotlight on an empty stage.
                <div
                    aria-label={altText}
                    className="absolute inset-0 flex items-center justify-center"
                    role="img"
                >
                    <Mic
                        className="h-14 w-14 text-champagne/35 sm:h-20 sm:w-20"
                        strokeWidth={1.25}
                        aria-hidden="true"
                    />
                    {/* stage-floor line where the spotlight pools */}
                    <span className="absolute inset-x-8 bottom-[30%] h-px bg-copper/20" />
                </div>
            )}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-4 sm:p-5">
                <p className="font-oswald text-sm font-medium uppercase tracking-[0.18em] text-copper-bright">
                    {formattedDate}
                </p>
                <p className="mt-1 font-urbanist-bold text-xl font-bold text-white sm:text-2xl">
                    {show.clubName ?? "Comedy show"}
                </p>
            </div>
        </div>
    );
};

const CompactShowCard: React.FC<{ show: ShowDTO }> = ({ show }) => {
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
    const outboundHref = buyUrl
        ? buildTicketOutboundHref({
              showId: show.id,
              clubId: show.clubId,
              destinationUrl: buyUrl,
              sourceSurface: "compact_show_card",
          })
        : "";
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
                style={{ background: COMPACT_CARD_SPOTLIGHT }}
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
                        className={`relative h-10 w-10 flex-none overflow-hidden rounded-full bg-coconut-cream ring-1 ring-copper/25 ${isSoldOut ? "grayscale opacity-60" : ""}`}
                    >
                        <Image
                            src={
                                imgError
                                    ? CLUB_PLACEHOLDER
                                    : parsedShow.imageUrl
                            }
                            onError={() => setImgError(true)}
                            alt={parsedShow.clubName ?? "Club"}
                            fill
                            className="object-contain"
                            sizes="40px"
                            aria-hidden="true"
                        />
                    </div>
                    <div className="min-w-0">
                        <p
                            data-testid="compact-show-title"
                            className="font-urbanist-bold font-bold text-foreground text-body leading-tight line-clamp-2"
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
                                <a
                                    href={outboundHref}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    aria-label={ticketAriaLabel}
                                    className="inline-block text-caption font-semibold text-copper-bright font-dmSans hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                                >
                                    {ticketLabel || "Get Tickets"}
                                </a>
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

export default ShowCard;
