"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";

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

interface ShowCardProps {
    show: ShowDTO;
    hideClubName?: boolean;
}

const ShowCard: React.FC<ShowCardProps> = ({
    show,
    hideClubName,
}: ShowCardProps) => {
    const distanceMiles = show.distanceMiles ?? null;
    const { mv, mp } = useMotionProps();
    const parsedShow = new Show(show);
    const stillOnSale =
        parsedShow.tickets.filter((ticket) => !ticket.soldOut).length > 0;
    // Read before useEffect so first render always animates, remounts skip it
    const alreadySeen = seenShowIds.has(show.id);

    useEffect(() => {
        seenShowIds.add(show.id);
    }, [show.id]);

    const detailHref = `/show/${show.id}`;
    const detailLabel = parsedShow.name
        ? `View details for ${parsedShow.name}`
        : `View details for show at ${parsedShow.clubName ?? "comedy club"}`;

    return (
        <motion.article
            className="relative p-4 sm:p-6 bg-gradient-to-br from-[#FDF8EF] to-[#F5E6D3] overflow-hidden
                rounded-xl w-full shadow-md hover:shadow-xl border border-white/20"
            initial={alreadySeen ? false : { opacity: 0, y: mv(20) }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
            transition={{
                duration: mv(0.5),
                ease: "easeOut",
            }}
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
                            />
                        </div>

                        {parsedShow.tickets.length > 0 && (
                            <div className="sm:self-start relative z-[2]">
                                <FullRoundedButton
                                    href={
                                        stillOnSale
                                            ? parsedShow.tickets[0].purchaseUrl
                                            : null
                                    }
                                    label={
                                        stillOnSale ? "Get Tickets" : "Sold Out"
                                    }
                                    color={
                                        stillOnSale ? "bg-copper" : "bg-red-500"
                                    }
                                    disabled={!stillOnSale}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                />
                            </div>
                        )}
                    </div>

                    <div className="lg:hidden relative z-[2]">
                        <Divider />
                        <div className="pt-2 sm:pt-4">
                            <LineupGrid lineup={parsedShow.lineup} />
                        </div>
                    </div>
                </div>

                <div className="hidden lg:block lg:w-[65%] relative z-[2]">
                    <LineupGrid lineup={parsedShow.lineup} />
                </div>
            </div>
        </motion.article>
    );
};

export default ShowCard;
