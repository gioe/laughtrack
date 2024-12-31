"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import Link from "next/link";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import ClubMarquee from "../../image/club";
import ComedianHeadshot from "../../image/comedian";
interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }) => {
    const dateObject = moment(new Date(show.date ?? new Date()));
    const clubName = show.clubName ?? "";
    const ticket = show.ticket;
    const showName = show.name;
    const lineup = show.containedEntities;

    return (
        <main
            className="flex flex-col items-center mt-3 mb-3 px-2 pr-4 border-b
        transition duration-200 rounded-3xl ease-out first:border-t bg-locust"
        >
            <section className="grid bg-green-500 grid-cols-5 -gap-x-5 gap-y-3">
                {lineup.map((comedian: Comedian) => (
                    <div className="hover:z-10">
                        <ComedianHeadshot
                            key={comedian.name}
                            priority={false}
                            comedian={comedian}
                            size="m"
                            type="rounded"
                        />
                    </div>
                ))}
            </section>
            {lineup.length > 0 && (
                <section className="flex flex-col bg-red-800 items-center align-middle w-full">
                    <h3 className="font-bebas font-semibold text-copper pb-3 text-xl">
                        Featuring:
                    </h3>
                    <div className="grid grid-cols-2 grid-rows-7 space-1 bg-blue-800 w-full">
                        {lineup.map((comedian: Comedian) => {
                            return (
                                <h1 key={comedian.name} className="font-fjalla">
                                    {comedian.name}
                                </h1>
                            );
                        })}
                    </div>
                </section>
            )}

            <section>
                <h1 className="text-m ml-2 text-center">
                    {`${dateObject.format("LT LL")}`}
                </h1>
                <h1 className="text-center mt-8 text-sm">{`$${ticket.price.toString()}`}</h1>
                <Link
                    className="text-center text-sm underline"
                    href={ticket.link}
                >
                    <p className="text-m ml-2 text-center">Get tickets</p>
                </Link>
            </section>
        </main>
    );
};

export default ShowCard;
