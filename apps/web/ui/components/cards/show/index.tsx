"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Mic } from "lucide-react";
import { Button } from "@/ui/components/ui/button";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";
import EntityCard from "../entity";
import { formatShowDate } from "@/util/dateUtil";
import { hasUnknownAvailableTicketPrice } from "@/util/ticket/ticketUtil";
import PriceUnavailableInfo from "@/ui/components/tickets/PriceUnavailableInfo";

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

// Backdrop for the visual panel: a single spotlight cone from above + a copper
// floor pool below over a warm near-black, evoking a comedy-club stage.
const STAGE_BACKDROP =
    "radial-gradient(120% 82% at 50% -14%, rgba(247,231,206,0.20), rgba(247,231,206,0.05) 38%, transparent 66%)," +
    "radial-gradient(72% 36% at 50% 106%, rgba(184,115,51,0.18), transparent 70%)," +
    "linear-gradient(180deg, #1c140e 0%, #100b08 100%)";

export type ShowCardContext = "default" | "comedian-detail";

interface ShowCardProps {
    show: ShowDTO;
    hideClubName?: boolean;
    variant?: "default" | "past";
    context?: ShowCardContext;
}

const ShowCard: React.FC<ShowCardProps> = ({
    show,
    hideClubName,
    variant = "default",
    context = "default",
}: ShowCardProps) => {
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
                                                <Link
                                                    href={purchaseUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    aria-label={ticketLabel}
                                                >
                                                    Get Tickets
                                                </Link>
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
                    className="object-cover"
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
                <p className="mt-1 font-gilroy-bold text-xl font-bold text-white sm:text-2xl">
                    {show.clubName ?? "Comedy show"}
                </p>
            </div>
        </div>
    );
};

export default ShowCard;
