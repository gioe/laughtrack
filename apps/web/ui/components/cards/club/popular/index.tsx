"use client";

import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import EntityCard from "../../entity";
import { Building2 } from "lucide-react";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface PopularClubCardProps {
    entity: ClubDTO;
}

const PopularClubCard: React.FC<PopularClubCardProps> = ({ entity }) => {
    const club = new Club(entity);
    const [error, setError] = useState(false);
    const showFallback =
        error || !club.imageUrl || club.imageUrl === PLACEHOLDER;

    return (
        <EntityCard chrome="none" className="w-full">
            <div className="relative w-full aspect-square rounded-xl overflow-hidden mb-4 hover:cursor-pointer bg-coconut-cream">
                <Link
                    href={`/club/${club.name}`}
                    className="block w-full h-full relative"
                >
                    {showFallback ? (
                        <div
                            data-testid="club-image-fallback"
                            className="flex h-full w-full flex-col items-center justify-center gap-3 bg-gradient-to-br from-coconut-cream via-white to-copper/20 p-6 text-center text-cedar"
                        >
                            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/85 text-copper shadow-sm">
                                <Building2
                                    size={32}
                                    strokeWidth={1.8}
                                    aria-hidden="true"
                                />
                            </span>
                            <span className="text-sm font-bold font-gilroy-bold leading-tight">
                                {club.name}
                            </span>
                        </div>
                    ) : (
                        <Image
                            src={club.imageUrl}
                            alt={club.name}
                            fill
                            className="object-cover"
                            onError={() => setError(true)}
                            sizes="(max-width: 319px) calc(100vw - 2rem), (max-width: 640px) 280px, 320px"
                            priority={false}
                        />
                    )}
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
