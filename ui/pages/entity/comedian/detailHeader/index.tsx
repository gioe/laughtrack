"use client";

import React, { useState } from "react";
import { Heart } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../socialColumn";
import { useFavorite } from "@/hooks/useFavorite";
import Image from "next/image";

const PLACEHOLDER = "/images/comedian-placeholder.png";

interface ClubDetailHeaderProps {
    comedian: ComedianDTO;
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    comedian,
}) => {
    const [error, setError] = useState(false);

    const parsedComedian = new Comedian(comedian);

    const { isFavorite, handleFavoriteClick } = useFavorite({
        initialState: parsedComedian.isFavorite ?? false,
        entityId: comedian.uuid,
    });

    return (
        <div className="w-full max-w-7xl mx-auto px-6 py-8">
            <div className="flex flex-col md:flex-row gap-8">
                {/* Left column with name and image */}
                <div className="flex-1">
                    <h1 className="text-[32px] font-bold font-gilroy-bold mb-6">
                        {parsedComedian.name}
                    </h1>
                    <div className="relative aspect-[4/3] w-full max-w-md rounded-lg overflow-hidden">
                        <Image
                            src={error ? PLACEHOLDER : comedian.imageUrl}
                            alt={comedian.name}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 100vw, 384px"
                            onError={() => setError(true)}
                            priority
                        />
                    </div>
                </div>

                {/* Right column with actions and social links */}
                <div className="w-full md:w-80">
                    <div className="flex gap-4 mb-8">
                        <button
                            onClick={handleFavoriteClick}
                            className={`flex items-center gap-2 ${
                                isFavorite
                                    ? "text-red-700 hover:text-red-800"
                                    : "text-copper hover:text-copper"
                            } transition-colors duration-200 disabled:opacity-50`}
                        >
                            <Heart
                                className={`w-4 h-4 ${isFavorite ? "fill-current" : ""}`}
                            />
                            <span className="text-copper font-dmSans font-semibold text-[16px]">
                                {isFavorite
                                    ? "Remove from Favorites"
                                    : "Add to Favorites"}
                            </span>
                        </button>
                    </div>

                    <div className="space-y-4">
                        <h2 className="text-[22px] font-bold font-gilroy-bold mb-4">
                            Social Media
                        </h2>
                        <SocialMediaColumn comedian={comedian} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ComedianDetailHeader;
