"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import ClubMarquee from "../../image/club";
import { timeFromMoment } from "../../../util/dateUtil";
import LineupGrid from "../../grid/lineup";
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
        <main
            className="flex flex-col md:flex-row md:items-stretch bg-locust 
        rounded-3xl"
        >
            <div
                className="flex flex-row md:flex-col m-2 gap-2 top-0 left-0
             translate-x-1 translate-y-1 rounded-3x basis-1/6"
            >
                <div
                    className="hover:z-9 hover:scale-105 rounded-2xl transform 
                    transition duration-300 ease-outsize-16"
                >
                    <ClubMarquee priority size="s" name={clubName} />
                </div>
                <div className="size-16 rounded-2xl mb-2">
                    <DateMarquee date={dateObject} />
                </div>
            </div>
            <div className="flex flex-col gap-2 m-3 basis-1/2">
                {lineup.length > 0 && (
                    <div
                        className="flex flex-col items-center m-3
                gap-4"
                    >
                        <h3
                            className="font-bebas font-semibold
        text-pine-tree text-3xl"
                        >
                            Featuring:
                        </h3>
                        <div>
                            <LineupGrid lineup={lineup} />
                        </div>
                    </div>
                )}
                <div className="flex flex-col gap-2 m-3">
                    <h1 className="text-2xl text-center text-copper font-fjalla">{`${showName}`}</h1>

                    {show.description && (
                        <h1 className="text-m text-center">{`${show.description}`}</h1>
                    )}
                    <h1 className="font-fjalla text-copper text-2xl text-center">
                        {`${timeFromMoment(dateObject)}`}
                    </h1>
                    <div>
                        <TicketDetail ticket={ticket} />
                    </div>
                </div>
            </div>
        </main>
    );
};

export default ShowCard;
