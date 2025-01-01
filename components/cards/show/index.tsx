"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import Link from "next/link";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import ClubMarquee from "../../image/club";
import {
    dateWithOrdinalFromMoment,
    monthFromMoment,
    timeFromMoment,
} from "../../../util/dateUtil";
import LineupGrid from "../../grid/lineup";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }) => {
    const dateObject = moment(new Date(show.date ?? new Date()));
    const clubName = show.clubName ?? "";
    const ticket = show.ticket;
    const showName = show.name;
    const lineup = show.lineup;

    console.log(lineup);

    const getFirstName = (comedian: Comedian) => {
        return comedian.name.split(" ")[0];
    };

    const getLastName = (comedian: Comedian) => {
        return comedian.name.split(" ")[1];
    };
    return (
        <main className="flex flex-col lg:flex-row bg-locust rounded-3xl max-w-screen-lg">
            <div className="absolute top-0 left-0 translate-x-2.5 translate-y-2.5 rounded-3xl bg-red-900">
                <ClubMarquee
                    priority
                    size="m"
                    type="rounded"
                    club={{
                        name: clubName,
                        count: 0,
                    }}
                />
            </div>
            <div className="basis-1/4 flex flex-col items-center justify-center bg-blue-gray-700">
                <div className="flex flex-col">
                    <h1 className="font-fjalla text-copper text-3xl text-center">
                        {`${monthFromMoment(dateObject)}`}
                    </h1>
                    <h1 className="font-fjalla text-copper text-3xl text-center">
                        {`${dateWithOrdinalFromMoment(dateObject)}`}
                    </h1>
                </div>
            </div>
            {lineup.length > 0 && (
                <section className="flex flex-col items-center p-10 gap-5 bg-red-100">
                    <div className="flex flex-col lg:flex-row gap-6">
                        <h3 className="font-bebas font-semibold text-copper text-3xl">
                            {`${clubName}`}
                        </h3>
                        <h3 className="font-bebas font-semibold text-pine-tree text-3xl">
                            Presents:
                        </h3>
                    </div>
                    {/* <LineupGrid lineup={lineup} /> */}
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
                <h1 className="text-center text-m text-pine-tree font-fjalla">{`$${ticket.price.toString()}`}</h1>
                <Link
                    className="text-sm text-center underline"
                    href={ticket.link}
                >
                    <p className="font-fjalla text-copper text-center">
                        Get tickets
                    </p>
                </Link>
            </section>
        </main>
    );
};

export default ShowCard;
