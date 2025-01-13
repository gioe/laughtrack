"use client";

import React from "react";
import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/grid/lineup";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }: ShowCardProps) => {
    return (
        <div className="p-6 bg-[#FDF8EF]">
            <div className="flex items-center justify-between mb-8">
                <ShowCardHeader show={show} />

                <FullRoundedButton
                    href={show.ticket.link}
                    label="Get Tickets"
                />
            </div>

            <LineupGrid lineup={show.lineup} />
        </div>
    );
};

export default ShowCard;
