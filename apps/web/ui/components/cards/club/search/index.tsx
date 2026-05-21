"use client";

import { Heart, MapPin } from "lucide-react";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import EntityCard from "../../entity";
import { useFavorite } from "@/hooks/useFavorite";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ClubSearchCardProps {
    club: ClubDTO;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const [error, setError] = useState(false);
    const locationLabel =
        parsedClub.city && parsedClub.state
            ? `${parsedClub.city}, ${parsedClub.state}`
            : parsedClub.city || parsedClub.address;

    const clubId = club.id;
    const canFavorite = typeof clubId === "number" && clubId > 0;
    const { isFavorite, handleFavoriteClick, isAuthenticated } = useFavorite({
        initialState: club.is_Favorite ?? false,
        entityId: canFavorite ? String(clubId) : "0",
        entityType: "club",
    });
    const favoriteLabel = isAuthenticated
        ? isFavorite
            ? `Remove ${parsedClub.name} from favorites`
            : `Add ${parsedClub.name} to favorites`
        : `Sign in to favorite ${parsedClub.name}`;

    return (
        <EntityCard chrome="coconut-hover" className="pb-4 px-4 h-full">
            <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-white p-3">
                <Link
                    href={`/club/${parsedClub.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={`${parsedClub.name}`}
                        fill
                        className="object-contain"
                        onError={() => setError(true)}
                        sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                        priority={false}
                    />
                </Link>
                {canFavorite && (
                    <button
                        type="button"
                        onClick={handleFavoriteClick}
                        aria-label={favoriteLabel}
                        aria-pressed={isAuthenticated ? isFavorite : undefined}
                        className={`absolute right-2 top-2 z-10 rounded-full bg-white/90 p-2 text-gray-700 shadow-sm transition hover:bg-white hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-copper ${
                            isAuthenticated
                                ? ""
                                : "border border-dashed border-gray-400"
                        }`}
                    >
                        <Heart
                            aria-hidden="true"
                            className={`h-5 w-5 ${
                                isFavorite ? "fill-current text-red-500" : ""
                            }`}
                        />
                    </button>
                )}
            </div>
            <div className="mt-4 space-y-2">
                <h3 className="text-h3 font-extrabold font-gilroy-bold text-center text-foreground hover:text-foreground transition-colors">
                    {parsedClub.name}
                </h3>

                <p className="text-body text-gray-600 text-center font-dmSans">
                    {locationLabel}
                </p>

                {club.chainName && (
                    <p className="text-xs text-gray-500 text-center font-dmSans">
                        {club.chainName}
                    </p>
                )}

                <div className="flex justify-center">
                    <span className="bg-copper/10 text-copper text-xs px-2 py-0.5 rounded-full font-dmSans">
                        {`${parsedClub.showCount ?? 0} upcoming shows`}
                    </span>
                </div>
                {club.distanceMiles != null && (
                    <p className="flex items-center justify-center gap-1 text-xs text-gray-500 font-dmSans">
                        <MapPin size={11} aria-hidden="true" />
                        {club.distanceMiles < 1
                            ? "< 1 mile away"
                            : `${Math.round(club.distanceMiles)} miles away`}
                    </p>
                )}
            </div>
        </EntityCard>
    );
};

export default ClubSearchCard;
