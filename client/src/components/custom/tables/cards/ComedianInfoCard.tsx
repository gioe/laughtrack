'use client';

import { useState, useEffect } from 'react'
import React from "react";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { HeartIcon as OutlineHeart } from "@heroicons/react/outline";
import { HeartIcon as SolidHeart } from "@heroicons/react/solid";
import Image from "next/image";
import Link from "next/link";

interface ComedianInfoCardProps {
    userIsFollower?: boolean;
    comedian: ComedianInterface;
}

const ComedianInfoCard: React.FC<ComedianInfoCardProps> = ({
    userIsFollower,
    comedian
}) => {

    const [isFollower, setIsFollower] = useState(userIsFollower ?? false)

    const handleFollowClick = (event: any) => {
        if (isFollower) {
            setIsFollower(false)
        } else {
            setIsFollower(true)
        }
    }


    return (
        <div className="flex flex-row bg-orange-500 rounded-xl shadow-md overflow-hidden md:max-w-2xl items-start">
            <div className='bg-green-800 flex-1'>
                <Link
                    href={`/comedian/${comedian.name}`}
                >
                    <div className="relative p-5 m-5 object-fill lg:h-40 lg:w-40 sm:h-40">
                        <Image alt="Comedian"
                            src={`/images/comedians/square/${comedian.name}.png`}
                            fill
                            priority={false}
                            style={{ objectFit: "cover" }}
                            className="rounded-badge" />
                    </div>
                </Link>

            </div>
            <div className="bg-red-900 flex-1">
                <div className="flex flex-col bg-yellow-400">
                <div className="flex flex-row-reverse items-end">
                {
                            isFollower ?
                                <SolidHeart onClick={handleFollowClick} className="h-7 cursor-pointer"></SolidHeart> :
                                <OutlineHeart onClick={handleFollowClick} className="h-7 cursor-pointer" />
                        }

                    </div>

                    <h4 className="m:text-sm text-m text-left bg-blue-900">{comedian.name}</h4>
                </div>
            </div>
    </div>
    )
}

export default ComedianInfoCard;