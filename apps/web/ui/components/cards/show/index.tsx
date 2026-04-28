"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/ui/components/ui/button";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";
import EntityCard from "../entity";
import { formatShowDate } from "@/util/dateUtil";

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
const ARTWORK_PLACEHOLDER_THEMES = [
    "radial-gradient(circle at 20% 20%, rgba(246,205,166,0.36), transparent 28%), linear-gradient(135deg, #2f3a34 0%, #704932 55%, #c17f53 100%)",
    "radial-gradient(circle at 78% 18%, rgba(255,244,214,0.3), transparent 30%), linear-gradient(135deg, #5a2430 0%, #8b5f3d 52%, #d39a64 100%)",
    "radial-gradient(circle at 28% 74%, rgba(244,191,111,0.32), transparent 28%), linear-gradient(135deg, #263f48 0%, #79543f 58%, #d08a55 100%)",
    "radial-gradient(circle at 72% 70%, rgba(255,225,184,0.34), transparent 30%), linear-gradient(135deg, #3c3145 0%, #76503f 54%, #ba724c 100%)",
];

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
    const stillOnSale =
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
    const renderVisualPanel = () =>
        context === "comedian-detail" ? (
            <ShowCardArtwork show={parsedShow} />
        ) : (
            <LineupGrid lineup={parsedShow.lineup} />
        );

    return (
        <EntityCard
            as="article"
            chrome="warm"
            className={
                isPast
                    ? "relative p-4 sm:p-6 overflow-hidden w-full shadow-sm hover:shadow-md border-white/10 bg-gradient-to-br from-stone-50 to-coconut-cream/45"
                    : "relative p-4 sm:p-6 overflow-hidden w-full hover:shadow-xl"
            }
            animateEntryY={isPast ? undefined : 20}
            alreadySeen={alreadySeen}
        >
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
                            <p className="sm:self-start relative z-[2] rounded-full border border-copper/15 bg-white/55 px-3 py-1.5 text-sm font-dmSans text-gray-500">
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
                                return (
                                    <div className="sm:self-start relative z-[2]">
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
    const dateForTheme = new Date(show.date);
    const placeholderTheme =
        ARTWORK_PLACEHOLDER_THEMES[
            Math.abs(show.id + dateForTheme.getUTCDate()) %
                ARTWORK_PLACEHOLDER_THEMES.length
        ];

    return (
        <div className="pointer-events-none relative min-h-[176px] overflow-hidden rounded-lg border border-copper/10 bg-cedar text-coconut-cream shadow-inner sm:min-h-[220px] lg:min-h-[248px]">
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
                <div
                    aria-label={altText}
                    className="absolute inset-0"
                    role="img"
                    style={{ background: placeholderTheme }}
                />
            )}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-cedar/85 via-cedar/45 to-transparent p-4 sm:p-5">
                <p className="font-dmSans text-sm font-semibold uppercase tracking-[0.12em] text-coconut-cream/80">
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
