'use client';

import React from "react";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { HeartIcon as OutlineHeart } from "@heroicons/react/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/solid";
import Image from "next/image";
import Link from "next/link";

interface ComedianInfoCardProps {
    userIsFollower: boolean;
    comedian: ComedianInterface;
}

const ComedianInfoCard: React.FC<ComedianInfoCardProps> = ({
    userIsFollower,
    comedian
}) => {
    return (
        <div className="flex mt-3 py-7 px-2 pr-4 border-b 
        transition duration-200 rounded-lg ease-out first:border-t bg-silver-gray">
            <Link
                href={`/comedian/${comedian.name}`}
            >
                <div className="relative h-24 w-40 
            md:h-52 md:w-80 flex-shrink-0">
                    <Image alt="Comedian"
                        src={`/images/comedians/square/${comedian.name}.png`}
                        fill
                        priority={false}
                        sizes="100vw"
                        style={{ objectFit: "cover" }}
                        className="rounded-2xl" />
                </div>
            </Link>

            <div className="flex flex-col flex-grow pl-5">
                <div className="flex justify-between">
                    <p></p>
                    {
                        userIsFollower ?
                            <SolidHeart className="h-7 cursor-pointer"></SolidHeart> :
                            <OutlineHeart className="h-7 cursor-pointer" />
                    }

                </div>

                <h4 className="text-xl">{comedian.name}</h4>
            </div>

        </div>
    )
}

export default ComedianInfoCard;