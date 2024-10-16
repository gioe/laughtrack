'use client';

import React, { useState } from "react";
import MiniComedianIcon from "../../comedianIcons/MiniComedianIcon";
import moment from "moment";
import Image from "next/image";
import Link from "next/link";
import { ShowInterface } from "@/interfaces/show.interface";
import { LineupItem } from "@/interfaces/lineupItem.interface";

interface ShowInfoCardProps {
    show: ShowInterface;
}

const ShowInfoCard: React.FC<ShowInfoCardProps> = ({
    show
}) => {

    const [src, setSrc] = useState<string>(`/images/clubs/square/${show.clubName ?? ""}.png`);

    const onError = () => {
        setSrc(`/images/logo.png`);
    };

    const dateObject = moment(new Date(show.dateTime));

    return (
        <div className="flex flex-row mt-3 mb-3 px-2 pr-4 border-b 
        transition duration-200 rounded-lg ease-out first:border-t bg-silver-gray">
            <div className="grid grid-cols-2 divide-x">
                <div className="flex flex-col items-center ml-5 mr-4 mb-5 mt-1">
                    <h4 className="text-xl ml-2 text-center">{dateObject.format('LT')}</h4>
                    <div className="relative h-20 w-20 align-middle">
                        <Link
                            href={`/club/${show.clubName ?? ""}`}
                        >
                            <Image
                                alt="Club"
                                src={src}
                                fill
                                onError={onError}
                                priority={false}
                                style={{ objectFit: "cover" }}
                                className="rounded-2xl bg-orange-700">
                            </Image>
                        </Link>
                    </div>
                    <h4 className="text-xl ml-2 text-center">{show.clubName ?? ""}</h4>
                    <p className="text-m ml-2 text-center">{dateObject.format('LL')}</p>
                    <a className='text-center mt-8 text-sm underline' href={show.ticketLink}>Get tickets</a>
                </div>

                <section className="flex flex-col px-10">
                    <Link
                        href={`/show/${show.id}`}
                    >
                        <h4 className="text-m text-center">{show.name ?? ""}</h4>
                    </Link>
                    <div className="grid grid-cols-4 md:grid-cols-4 lg:grid-cols-4 gap-4 m-3 overflow-scrollscrollbar-hide">
                        {show.lineup
                            .sort((a, b) => b.popularityScore - a.popularityScore)
                            .map((item: LineupItem) => <MiniComedianIcon key={item.name} comedian={item} />)}
                    </div>
                </section>
            </div>

        </div>
    )
}

export default ShowInfoCard;