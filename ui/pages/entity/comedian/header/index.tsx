"use client";

import React, { useState } from "react";
import { Heart } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../social";
import { useFavorite } from "@/hooks/useFavorite";
import { getLocalCdnUrl } from "@/util/cdnUtil";

const PLACEHOLDER = getLocalCdnUrl("comedian-placeholder.png");

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
        <div className="max-w-7xl mx-auto p-6">
            {/* Header Section */}
            <div className="w-full  p-4">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                    <div className="flex items-center gap-4">
                        <img
                            src={error ? PLACEHOLDER : comedian.imageUrl}
                            alt={comedian.name}
                            className="w-16 h-16 rounded-full"
                            onError={() => setError(true)}
                        />
                        <div className="flex flex-col gap-1">
                            <h1 className="text-2xl font-bold text-gray-900">
                                {parsedComedian.name}
                            </h1>
                        </div>
                    </div>
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
                </div>
            </div>
            <SocialMediaColumn comedian={comedian} />
        </div>
    );
};

export default ComedianDetailHeader;
