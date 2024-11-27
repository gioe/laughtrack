"use client";

import React from "react";
import { Show } from "../../../objects/class/show/Show";
import ShowLineupSection from "./ShowLineupSection";
import ShowDetailsSection from "./ShowDetailsSection";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }) => {
    return (
        <div
            className="flex flex-row mt-3 mb-3 px-2 pr-4 border-b
        transition duration-200 rounded-lg ease-out first:border-t bg-silver-gray"
        >
            <ShowDetailsSection
                clubName={show.clubName}
                showDate={show.date}
                scrapedDate={show.lastScrapedDate}
                ticket={show.ticket}
            />

            <ShowLineupSection
                showId={show.id}
                showName={show.name}
                lineup={show.containedEntities}
            />
        </div>
    );
};

export default ShowCard;
