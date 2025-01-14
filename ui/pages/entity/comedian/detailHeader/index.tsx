"use client";

import React, { useState } from "react";
import { Heart } from "lucide-react";
import ImageGrid from "@/ui/components/grid/image";

interface ClubDetailHeaderProps {
    name: string;
    images: Array<{
        url: string;
        alt: string;
    }>;
    favorite: boolean;
    comedianId: number; // Added to identify the comedian for the API call
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    name,
    images,
    favorite,
    comedianId,
}) => {
    const [isFavorite, setIsFavorite] = useState(favorite);
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
                    comedianId,
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
                    <h1 className="text-3xl font-bold text-gray-900">{name}</h1>
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
            <ImageGrid images={images} />
        </div>
    );
};

export default ComedianDetailHeader;
