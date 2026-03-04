"use client";

import { Club } from "@/objects/class/club/Club";
import { getLocalCdnUrl } from "@/util/cdnUtil";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

const PLACEHOLDER = getLocalCdnUrl("club-placeholder.png");

interface PopularClubCardProps {
    entity: Club;
}

const PopularClubCard: React.FC<PopularClubCardProps> = ({ entity: club }) => {
    const [error, setError] = useState(false);

    return (
        <div className="w-full transition-transform duration-300 hover:scale-105">
            <div className="relative w-full aspect-square rounded-2xl overflow-hidden mb-4 hover:cursor-pointer">
                <Link
                    href={`/club/${club.name}`}
                    className="block w-full h-full relative"
                >
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={club.name}
                        fill
                        className="object-cover"
                        onError={() => setError(true)}
                        sizes="(max-width: 640px) 280px, 320px"
                        priority={false}
                    />
                </Link>
            </div>

            {/* Text Content */}
            <div className="space-y-1">
                <h2 className="text-[21px] font-bold leading-tight font-outfit">
                    {club.name}
                </h2>
                <p className="text-[16px] text-gray-600 font-dmSans">
                    {club.activeComedianCount} active comedians
                </p>
            </div>
        </div>
    );
};

export default PopularClubCard;
