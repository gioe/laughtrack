"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import LineupGrid from "../../grid/lineup";
import { FullRoundedButton } from "@/components/button/rounded/full";
import ShowCardHeader from "./header";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }: ShowCardProps) => {
    console.log(show);
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
