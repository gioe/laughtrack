"use client";

import React, { useState } from "react";
import { Heart } from "lucide-react";
import ImageGrid from "@/ui/components/grid/image";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../socialColumn";

interface ClubDetailHeaderProps {
    comedian: ComedianDTO;
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    comedian,
}) => {
    const parsedComedian = new Comedian(comedian);
    const [isFavorite, setIsFavorite] = useState(parsedComedian.isFavorite);
    const [isLoading, setIsLoading] = useState(false);

    const handleFavoriteClick = async () => {
        try {
            setIsLoading(true);

            const response = await fetch("/api/favorite", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    comedianId: parsedComedian.id,
                    isFavorite: !isFavorite,
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to update favorite status");
            }

            setIsFavorite(!isFavorite);
        } catch (error) {
            console.error("Error updating favorite status:", error);
            // You might want to show a toast or error message here
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header Section */}
            <div className="flex justify-between items-start mb-6">
                <div className="flex items-center gap-2">
                    <h1 className="text-3xl font-bold text-gray-900">
                        {parsedComedian.name}
                    </h1>
                </div>

                <button
                    onClick={handleFavoriteClick}
                    disabled={isLoading}
                    className={`flex items-center gap-2 ${
                        isFavorite
                            ? "text-red-700 hover:text-red-800"
                            : "text-copper hover:text-copper"
                    } transition-colors duration-200 disabled:opacity-50`}
                >
                    <Heart
                        className={`w-4 h-4 ${isFavorite ? "fill-current" : ""}`}
                    />
                    <span className="text-copper">
                        {isFavorite
                            ? "Remove from Favorites"
                            : "Add to Favorites"}
                    </span>
                </button>
            </div>

            {/* Image Grid */}
            <ImageGrid
                images={[
                    {
                        url: comedian.imageUrl,
                        alt: comedian.name,
                    },
                ]}
            />
            <div className="pb-4">
                <SocialMediaColumn comedian={comedian} />
            </div>
        </div>
    );
};

export default ComedianDetailHeader;
