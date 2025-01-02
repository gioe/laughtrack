"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import ClubMarquee from "../../image/club";
import { timeFromMoment } from "../../../util/dateUtil";
import LineupGrid from "../../grid/lineup";
import MarqueeTitle from "../../marquee/title";
import TicketDetail from "../../ticket";
import DateMarquee from "../../date";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }) => {
    const dateObject = moment(new Date(show.date ?? new Date()));
    const clubName = show.clubName ?? "";
    const ticket = show.ticket;
    const showName = show.name;
    const lineup = show.lineup;

    return (
        <main className="flex flex-col lg:flex-row bg-locust rounded-3xl m-2">
            <div
                className="flex flex-row lg:flex-col gap-4 relative top-0 left-0
             translate-x-2 translate-y-2 rounded-3x lg:w-20"
            >
                <ClubMarquee priority size="s" name={clubName} />
                <DateMarquee date={dateObject} />
            </div>
            {lineup.length > 0 && (
                <section
                    className="flex flex-col items-center p-6
                gap-4 bg-red-100"
                >
                    <MarqueeTitle name={clubName} />
                    <LineupGrid lineup={lineup} />
                </section>
            )}
            <section className="p-6 flex flex-col bg-brown-400 gap-2">
                <h1 className="text-m text-center text-copper font-fjalla">{`${showName}`}</h1>

                {show.description && (
                    <h1 className="text-m text-center">{`${show.description}`}</h1>
                )}
                <h1 className="font-fjalla text-copper text-2xl text-center">
                    {`${timeFromMoment(dateObject)}`}
                </h1>
                <TicketDetail ticket={ticket} />
            </section>
        </main>
    );
};

export default ShowCard;
