"use client";

import React from "react";
import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";

interface ShowCardProps {
    show: ShowDTO;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }: ShowCardProps) => {
    const parsedShow = new Show(show);

    return (
        <div className="p-6 bg-[#FDF8EF] overflow-hidden transition-transform duration-300 hover:scale-105 rounded-xl">
            <div className="flex items-center justify-between mb-8">
                <ShowCardHeader show={parsedShow} />

                <FullRoundedButton
                    href={parsedShow.ticket.link}
                    label={show.soldOut ? "Sold Out" : "Get Tickets"}
                    color={show.soldOut ? "bg-red-500" : "bg-copper"}
                />
            </div>

            {parsedShow.lineup.length > 0 && (
                <div>
                    <Divider />
                    <div className="pt-4">
                        <LineupGrid lineup={parsedShow.lineup} />
                    </div>
                </div>
            )}
        </div>
    );
};

export default ShowCard;
