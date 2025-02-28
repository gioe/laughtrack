"use client";

import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { getLocalCdnUrl } from "@/util/cdnUtil";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

const PLACEHOLDER = getLocalCdnUrl("club-placeholder.png");

interface ClubSearchCardProps {
    club: ClubDTO;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const [error, setError] = useState(false);

    return (
        <div className="bg-coconut-cream rounded-xl overflow-hidden pb-4 px-4">
            <div className="relative h-64">
                <Link
                    href={`/club/${parsedClub.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={`${parsedClub.name}`}
                        fill
                        className="object-cover rounded-xl"
                        onError={() => setError(true)}
                        sizes="(max-width: 768px) 100vw,
                               (max-width: 1200px) 50vw,
                               25vw"
                        priority={false}
                    />
                </Link>
            </div>
            <div className="mt-4">
                <h2 className="text-[22px] font-bold mb-1 font-outfit text-center">
                    {parsedClub.name}
                </h2>

                <p className="text-[18px] text-gray-600 mb-4 text-center font-dmSans">
                    {`${parsedClub.address}`}
                </p>
            </div>
        </div>
    );
};

export default ClubSearchCard;
