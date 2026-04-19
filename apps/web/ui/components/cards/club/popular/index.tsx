"use client";

import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import EntityCard from "../../entity";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface PopularClubCardProps {
    entity: ClubDTO;
}

const PopularClubCard: React.FC<PopularClubCardProps> = ({ entity }) => {
    const club = new Club(entity);
    const [error, setError] = useState(false);

    return (
        <EntityCard chrome="none" className="w-full">
            <div className="relative w-full aspect-square rounded-xl overflow-hidden mb-4 hover:cursor-pointer bg-coconut-cream p-3">
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
                        sizes="(max-width: 319px) calc(100vw - 2rem), (max-width: 640px) 280px, 320px"
                        priority={false}
                    />
                </Link>
            </div>

            {/* Text Content */}
            <div className="space-y-1">
                <h2 className="text-h3 font-bold leading-tight font-gilroy-bold">
                    {club.name}
                </h2>
                <p className="text-body text-gray-600 font-dmSans">
                    {club.activeComedianCount} active comedians
                </p>
            </div>
        </EntityCard>
    );
};

export default PopularClubCard;
