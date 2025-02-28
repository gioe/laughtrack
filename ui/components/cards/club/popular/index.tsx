"use client";

import { Club } from "@/objects/class/club/Club";
import { getLocalCdnUrl } from "@/util/cdnUtil";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

const PLACEHOLDER = getLocalCdnUrl("club-placeholder.png");

interface PopularClubCardProps {
    entity: string;
}

const PopularClubCard: React.FC<PopularClubCardProps> = ({ entity }) => {
    const club = JSON.parse(entity) as Club;
    const [error, setError] = useState(false);

    return (
        <div className="w-[218px] transition-transform duration-300 hover:scale-105">
            {/* Image Container */}
            <div className="relative w-[218px] h-[218px] rounded-2xl overflow-hidden mb-4 hover:cursor-pointer">
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
                        sizes="(max-width: 218px) 100vw, 218px"
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
