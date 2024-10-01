'use client';

import React from "react";
import { LineupItemInterface, ShowDetailsInterface } from "@/interfaces/show.interface";
import MiniComedianIcon from "../../comedianIcons/MiniComedianIcon";
import moment from "moment";
import Image from "next/image";
import Link from "next/link";

interface ShowInfoCardProps {
    show: ShowDetailsInterface;
}

const ShowInfoCard: React.FC<ShowInfoCardProps> = ({
    show
}) => {

    const dateObject = moment(new Date(show.dateTime));
    const description = `${dateObject.format('LT')} at ${show.club.name} in ${show.city} on ${dateObject.format('LL')}`

    return (
        <div className="flex flex-row mt-3 py-7 px-2 pr-4 border-b 
        transition duration-200 rounded-lg ease-out first:border-t bg-silver-gray">
            <div className="grid grid-cols-2 divide-x">
                <div className="flex flex-col items-center m-5">
                    <h4 className="text-xl ml-2 text-center">{dateObject.format('LT')}</h4>
                    <div className="relative h-20 w-20 align-middle">
                        <Link
                            href={`/club/${show.club.name}`}
                        >
                            <Image
                                alt="Club"
                                src={`/images/clubs/square/${show.club.name}.png`}
                                fill
                                priority={false}
                                style={{ objectFit: "cover" }}
                                className="rounded-2xl bg-orange-700">
                            </Image>
                        </Link>
                    </div>
                    <h4 className="text-xl ml-2 text-center">{show.club.name}</h4>
                    <p className="text-m ml-2 text-center">{dateObject.format('LL')}</p>
                    <a className='text-center mt-8 text-sm underline' href={show.ticketLink}>Get tickets</a>
                </div>

                <section>
                    <div className="grid grid-cols-3 gap-5 ml-10 overflow-scrollscrollbar-hide">
                        {show.lineup
                            .sort((a, b) => b.popularityScore - a.popularityScore)
                            .map((item: LineupItemInterface) => {
                                return (
                                    <MiniComedianIcon key={item.name} comedian={item} />
                                )
                            })}
                    </div>
                </section>
            </div>

        </div>
    )
}

export default ShowInfoCard;