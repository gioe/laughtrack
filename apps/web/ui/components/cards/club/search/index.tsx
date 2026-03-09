"use client";

import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ClubSearchCardProps {
    club: ClubDTO;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const [error, setError] = useState(false);

    return (
        <div className="bg-coconut-cream rounded-xl overflow-hidden pb-4 px-4 h-full transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
            <div className="relative w-full aspect-square">
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
                        sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                        priority={false}
                    />
                </Link>
            </div>
            <div className="mt-4 space-y-2">
                <h2 className="text-[22px] font-bold font-outfit text-center text-cedar hover:text-[#2D1810] transition-colors">
                    {parsedClub.name}
                </h2>

                <p className="text-[16px] text-gray-600 text-center font-dmSans">
                    {`${parsedClub.address}`}
                </p>
            </div>
        </div>
    );
};

export default ClubSearchCard;
