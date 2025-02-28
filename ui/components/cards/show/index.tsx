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
    const stillOnSale =
        parsedShow.tickets.filter((ticket) => !ticket.soldOut).length > 0;

    return (
        <div className="p-6 bg-[#FDF8EF] overflow-hidden transition-transform duration-300 hover:scale-105 rounded-xl">
            <div className="flex items-center justify-between mb-8">
                <ShowCardHeader show={parsedShow} />

                {parsedShow.tickets.length > 0 && (
                    <FullRoundedButton
                        href={parsedShow.tickets[0].purchaseUrl}
                        label={stillOnSale ? "Get Tickets" : "Sold Out"}
                        color={stillOnSale ? "bg-copper" : "bg-red-500"}
                    />
                )}
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
