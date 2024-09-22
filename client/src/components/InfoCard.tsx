import { ComedianInterface } from "@/interfaces/comedian.interface";
import React from "react";
import Image from "next/image"
import { HeartIcon } from "@heroicons/react/outline";

interface InfoCardProps {
    comedian: ComedianInterface;
}

const InfoCard: React.FC<InfoCardProps> = ({
    comedian
}) => {
    return (
        <div className="flex py-7 px-2 pr-4 
        border-b cursor-pointer hover:opacity-80 
        hover:shadow-lg transition duration-200 
        ease-out first:border-t">
            <div className="relative h-24 w-40 
            md:h-52 md:w-80 flex-shrink-0">
                <Image alt="Comedian"
                    src={'/images/banner.png'}
                    fill
                    objectFit="cover"
                    className="rounded-2xl" />
            </div>

            <div className="flex flex-col flex-grow pl-5">
                <div className="flex justify-between">
                    <p></p>
                    <HeartIcon className="h-7 cursor-pointer" />
                </div>

                <h4 className="text-xl">{comedian.name}</h4>

                <div className="border-b w-10 p-2" />

                <p className="p-2 text-sm text-gray-500 flex-grow">Shows</p>
            </div>

        </div>
    )
}

export default InfoCard;