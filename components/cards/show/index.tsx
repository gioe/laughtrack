"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import Link from "next/link";
import LinkedImage from "../../image/link";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import { Avatar, Tooltip } from "@material-tailwind/react";
import ClubMarquee from "../../image/club";
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
            className="flex items-center mt-3 mb-3 px-2 pr-4 border-b
        transition duration-200 rounded-lg ease-out first:border-t bg-locust"
        >
            <section className="flex flex-col items-center ml-5 mr-4 mb-5 mt-1">
                <ClubMarquee
                    priority
                    club={{
                        name: clubName,
                        count: 0,
                    }}
                />
            </section>
            <section className="flex flex-col px-10">
                <div className="flex items-center -space-x-3">
                    {lineup.map((comedian: Comedian) => (
                        <Tooltip key={comedian.name} content={comedian.name}>
                            <Avatar
                                key={comedian.name}
                                size="xl"
                                variant="circular"
                                alt={comedian.name}
                                src={`/images/comedian/square/${comedian.name}.png`}
                                className="border-2 border-locust hover:z-10"
                            />
                        </Tooltip>
                    ))}
                </div>
            </section>
            {lineup.length > 0 && (
                <section className="flex flex-col bg-red-800 items-center align-middle">
                    <h3 className="font-bebas font-semibold text-copper pb-3 text-xl">
                        Featuring:
                    </h3>
                    <div className="grid grid-cols-2 grid-rows-7 space-1 bg-blue-800">
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
