"use client";

import React, { useState } from "react";
import moment from "moment";
import Image from "next/image";
import { Show } from "@/objects/class/show/Show";
import { formatShowDate } from "@/util/dateUtil";
import { getLocalCdnUrl } from "@/util/cdnUtil";
import { formatTicketString } from "@/util/ticket/ticketUtil";
import { Ticket } from "@/objects/class/ticket/Ticket";

const PLACEHOLDER = getLocalCdnUrl("club-placeholder.png");

interface ShowCardHeaderProps {
    show: Show;
}

const ShowCardHeader: React.FC<ShowCardHeaderProps> = ({
    show,
}: ShowCardHeaderProps) => {
    const [error, setError] = useState(false);

    return (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="relative w-12 h-12 sm:w-16 sm:h-16 rounded-full overflow-hidden hidden sm:block">
                <Image
                    src={error ? PLACEHOLDER : show.imageUrl}
                    onError={() => setError(true)}
                    alt={show.clubName ?? "Club logo"}
                    fill
                    className="object-cover"
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
