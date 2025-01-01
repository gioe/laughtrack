"use client";

import { Show } from "../../../objects/class/show/Show";
import React from "react";
import moment from "moment";
import Link from "next/link";
import { Comedian } from "../../../objects/class/comedian/Comedian";
import ComedianHeadshot from "../../image/comedian";
import ClubMarquee from "../../image/club";

interface ShowCardProps {
    show: Show;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }) => {
    const dateObject = moment(new Date(show.date ?? new Date()));
    const clubName = show.clubName ?? "";
    console.log(show.ticket);
    const ticket = show.ticket;
    const showName = show.name;
    const lineup = show.containedEntities;

    const getFirstName = (comedian: Comedian) => {
        return comedian.name.split(" ")[0];
    };

    const getLastName = (comedian: Comedian) => {
        return comedian.name.split(" ")[1];
    };
    return (
        <main
            className="flex
        transition duration-200 ease-out bg-locust"
        >
            <div className="bg-red-500 relative">
                <div className="top-0 left-0 translate-x-2.5 translate-y-2.5 rounded-3xl">
                    <ClubMarquee
                        priority
                        club={{
                            name: clubName,
                            count: 0,
                        }}
                    />
                </div>
            </div>
            {lineup.length > 0 && (
                <div className="flex-1 bg-green-500">
                    <div
                        className="flex flex-col items-center
transition duration-200 rounded-3xl ease-out bg-green-500"
                    >
                        <section className="flex flex-col items-center p-10">
                            <div className="flex flex-row gap-6 pb-5">
                                <h3 className="font-bebas font-semibold text-copper text-3xl">
                                    {`${clubName}`}
                                </h3>
                                <h3 className="font-bebas font-semibold text-pine-tree text-3xl">
                                    Presents:
                                </h3>
                            </div>
                            <div className="flex flex-row gap-4 bg-black">
                                {lineup.map((comedian: Comedian) => (
                                    <div
                                        key={comedian.id.toString()}
                                        className="hover:z-9 hover:scale-105 transform transition
duration-300 ease-out bg-blue-800 flex flex-col items-center"
                                    >
                                        <ComedianHeadshot
                                            priority={false}
                                            comedian={comedian}
                                            size="m"
                                            type="rounded"
                                        />
                                        {comedian.name
                                            .split(" ")
                                            .map((nameString) => {
                                                return (
                                                    <h1
                                                        key={nameString}
                                                        className="font-fjalla text-center bg-red-500 w-full"
                                                    >
                                                        {`${nameString}`}
                                                    </h1>
                                                );
                                            })}
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>
                </div>
            )}
            <div className="flex-1 bg-blue-500">
                <section className=" p-10">
                    <h1 className="text-m ml-2 text-center">{`${showName}`}</h1>
                    {show.description && (
                        <h1 className="text-m ml-2 text-center">{`${show.description}`}</h1>
                    )}
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
            </div>
        </main>
    );
};

export default ShowCard;
