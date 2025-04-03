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
        <div className="p-2 sm:p-6 bg-gradient-to-br from-[#FDF8EF] to-[#F5E6D3] overflow-hidden transition-all duration-300 hover:scale-[1.02] rounded-xl w-full shadow-md hover:shadow-xl border border-white/20">
            <div className="flex flex-col lg:flex-row gap-2 sm:gap-4">
                <div className="flex-1 lg:w-[35%] flex flex-col gap-2 sm:gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-4">
                        <div className="flex-1">
                            <ShowCardHeader show={parsedShow} />
                        </div>

                        {parsedShow.tickets.length > 0 && (
                            <div className="sm:self-start">
                                <FullRoundedButton
                                    href={parsedShow.tickets[0].purchaseUrl}
                                    label={
                                        stillOnSale ? "Get Tickets" : "Sold Out"
                                    }
                                    color={
                                        stillOnSale ? "bg-copper" : "bg-red-500"
                                    }
                                />
                            </div>
                        )}
                    </div>

                    {parsedShow.lineup.length > 0 && (
                        <div className="lg:hidden">
                            <Divider />
                            <div className="pt-2 sm:pt-4">
                                <LineupGrid lineup={parsedShow.lineup} />
                            </div>
                        </div>
                    )}
                </div>

                {parsedShow.lineup.length > 0 && (
                    <div className="hidden lg:block lg:w-[65%]">
                        <LineupGrid lineup={parsedShow.lineup} />
                    </div>
                )}
            </div>
        </div>
    );
};

export default ShowCard;
