'use client';

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ClubInterface } from "@/interfaces/club.interface";

interface ClubInfoCardProps {
    club: ClubInterface;
}

const ClubInfoCard: React.FC<ClubInfoCardProps> = ({
    club
}) => {

    const [src, setSrc] = useState<string>(`/images/clubs/square/${club.name}.png`);
    
    const onError = () => {
      setSrc(`/images/logo.png`);
    };
    
    return (
        <div className="flex flex-row bg-orange-500 rounded-xl shadow-md overflow-hidden md:max-w-2xl items-start">
            <div className='bg-green-800 flex-1'>
                <Link
                    href={`/club/${club.name}`}
                >
                    <div className="relative p-5 m-5 object-fill lg:h-40 lg:w-40 sm:h-40">
                        <Image alt="Comedian"
                            src={src}
                            fill
                            priority={false}
                            onError={onError}
                            style={{ objectFit: "cover" }}
                            className="rounded-badge" />
                    </div>
                </Link>

            </div>
            <div className="bg-red-900 flex-1">
                <div className="flex flex-col bg-yellow-400">
                    <h4 className="m:text-sm text-m text-left bg-blue-900">{club.name}</h4>
                </div>
            </div>
        </div>
    )
}

export default ClubInfoCard;