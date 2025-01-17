"use client";

import React from "react";
import moment from "moment";
import Image from "next/image";
import { Show } from "@/objects/class/show/Show";
import { formatShowDate } from "@/util/dateUtil";

interface ShowCardHeaderProps {
    show: Show;
}

const ShowCardHeader: React.FC<ShowCardHeaderProps> = ({
    show,
}: ShowCardHeaderProps) => {
    const dateObject = moment(new Date(show.date ?? new Date()));
    const ticket = show.ticket;

    return (
        <div className="flex items-center gap-4">
            {/* Venue Logo */}
            <div className="relative w-16 h-16 rounded-full overflow-hidden">
                <Image
                    src={show.imageUrl}
                    alt={show.clubName ?? "Club logo"}
                    fill
                    className="object-cover"
                />
            </div>

            {/* Venue Details */}
            <div>
                <h2 className="text-[24px] font-inter font-bold text-[#2D1810] mb-1">
                    {show.clubName ?? ""}
                </h2>
                {show.name && (
                    <p className="text-gray-600 font-dmSans text-[18px]  mb-1">
                        {`${show.name}`}
                    </p>
                )}
                <p className="text-gray-600 font-dmSans text-[18px]">
                    {formatShowDate(show.date.toString())} · {`${show.address}`}
                </p>
                <p className="text-[#CD7F32] font-semibold mt-1 font-inter text-[20px]">{`$${ticket.price.toString()}`}</p>
            </div>
        </div>
    );
};

export default ShowCardHeader;
