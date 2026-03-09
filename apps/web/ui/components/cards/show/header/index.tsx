"use client";

import React, { useState } from "react";
import Image from "next/image";
import { Show } from "@/objects/class/show/Show";
import { formatShowDate } from "@/util/dateUtil";
import { formatTicketString } from "@/util/ticket/ticketUtil";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ShowCardHeaderProps {
    show: Show;
}

const ShowCardHeader: React.FC<ShowCardHeaderProps> = ({
    show,
}: ShowCardHeaderProps) => {
    const [error, setError] = useState(false);

    return (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="relative aspect-square w-[12%] min-w-[48px] max-w-[64px] rounded-full overflow-hidden">
                <Image
                    src={error ? PLACEHOLDER : show.imageUrl}
                    onError={() => setError(true)}
                    alt={show.clubName ?? "Club logo"}
                    fill
                    className="object-cover"
                    sizes="(max-width: 48px) 48px, 64px"
                />
            </div>

            <div>
                <h2 className="text-xl sm:text-2xl md:text-[24px] font-inter font-bold text-[#2D1810] mb-1">
                    {show.clubName ?? ""}
                </h2>
                {show.name && (
                    <p className="text-base sm:text-lg md:text-[18px] text-gray-600 font-dmSans mb-1">
                        {`${show.name}`}
                    </p>
                )}
                <p className="text-base sm:text-lg md:text-[18px] text-gray-600 font-dmSans">
                    {formatShowDate(show.date.toString())} · {`${show.address}`}
                </p>
                {!show.soldOut && (
                    <p className="text-lg sm:text-xl md:text-[20px] text-copper font-semibold mt-1 font-inter">
                        {formatTicketString(
                            show.tickets.filter((ticket) => !ticket.soldOut),
                        )}
                    </p>
                )}
            </div>
        </div>
    );
};

export default ShowCardHeader;
