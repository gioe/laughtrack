"use client";

import React from "react";
import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";

interface ShowCardProps {
    show: string;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }: ShowCardProps) => {
    const showDto = JSON.parse(show) as ShowDTO;
    const parsedShow = new Show(showDto);
    return (
        <div className="p-6 bg-[#FDF8EF] overflow-hidden transition-transform duration-300 hover:scale-105 hover:cursor-pointer rounded-xl">
            <div className="flex items-center justify-between mb-8">
                <ShowCardHeader show={parsedShow} />

                <FullRoundedButton
                    href={parsedShow.ticket.link}
                    label="Get Tickets"
                />
            </div>

            <LineupGrid lineup={parsedShow.lineup} />
        </div>
    );
};

export default ShowCard;
