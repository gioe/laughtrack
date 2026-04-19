"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { Show } from "@/objects/class/show/Show";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { formatShowDate } from "@/util/dateUtil";
import { formatTicketString } from "@/util/ticket/ticketUtil";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface CompactShowCardProps {
    show: ShowDTO;
}

const CompactShowCard: React.FC<CompactShowCardProps> = ({ show }) => {
    const { mp } = useMotionProps();
    const [imgError, setImgError] = useState(false);
    const parsedShow = new Show(show);

    const availableTickets = parsedShow.tickets.filter((t) => !t.soldOut);
    const ticketLabel = formatTicketString(availableTickets);
    const buyUrl =
        availableTickets.length > 0
            ? availableTickets[0].purchaseUrl
            : undefined;

    const lineupNames = parsedShow.lineup.map((c) => c.name).filter(Boolean);
    const displayNames = lineupNames.slice(0, 2).join(", ");
    const extraCount = lineupNames.length - 2;

    const detailHref = `/show/${show.id}`;
    const detailLabel = parsedShow.name
        ? `View details for ${parsedShow.name}`
        : `View details for show at ${parsedShow.clubName ?? "comedy club"}`;

    return (
        <motion.article
            className="relative flex flex-col gap-3 p-4 bg-gradient-to-br from-[#FDF8EF] to-[#F5E6D3]
                rounded-xl shadow-md border border-white/20 h-full"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
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

            {/* Club header */}
            <div className="flex items-center gap-3">
                <div className="relative w-10 h-10 rounded-full overflow-hidden flex-none">
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
                    <p className="font-gilroy-bold font-bold text-[#2D1810] text-[15px] leading-tight line-clamp-2">
                        {parsedShow.clubName}
                    </p>
                    {parsedShow.name && (
                        <p className="text-xs text-gray-500 font-dmSans leading-snug line-clamp-2">
                            {parsedShow.name}
                        </p>
                    )}
                    {parsedShow.room && (
                        <p className="text-xs text-gray-400 font-dmSans truncate">
                            {parsedShow.room}
                        </p>
                    )}
                </div>
            </div>

            {/* Date & address */}
            <div className="text-[13px] text-gray-600 font-dmSans space-y-0.5">
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
                <p className="text-[13px] text-gray-700 font-dmSans">
                    w/ {displayNames}
                    {extraCount > 0 && ` +${extraCount} more`}
                </p>
            )}

            {/* Ticket CTA */}
            {parsedShow.tickets.length > 0 && (
                <div className="mt-auto pt-1 relative z-[2]">
                    {buyUrl ? (
                        <Link
                            href={buyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block text-[13px] font-semibold text-copper font-dmSans hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
                        >
                            {ticketLabel || "Get Tickets"}
                        </Link>
                    ) : (
                        <span className="inline-block text-[11px] font-bold text-white bg-red-500 px-2.5 py-0.5 rounded-full font-dmSans">
                            Sold Out
                        </span>
                    )}
                </div>
            )}
        </motion.article>
    );
};

export default CompactShowCard;
