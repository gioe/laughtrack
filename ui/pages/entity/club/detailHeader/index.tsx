"use client";

import React, { useState } from "react";
import { MapPin } from "lucide-react";
import ImageGrid from "@/ui/components/grid/image";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";

interface ClubDetailHeaderProps {
    club: ClubDTO;
}

const ClubDetailHeader: React.FC<ClubDetailHeaderProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const [isLoading, setIsLoading] = useState(false);

    return (
        <div className="max-w-7xl mx-auto p-6">
            {/* Header Section */}
            <div className="w-full  p-4">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                    <div className="flex items-center gap-4">
                        <img
                            src={parsedClub.imageUrl}
                            alt={`${parsedClub.name} logo`}
                            className="w-16 h-16 rounded-full"
                        />
                        <div className="flex flex-col gap-1">
                            <h1 className="text-2xl font-bold text-gray-900">
                                {parsedClub.name}
                            </h1>
                            <div className="flex items-center gap-2 text-gray-600">
                                <MapPin className="w-4 h-4" />
                                <span>{parsedClub.address}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Image Grid */}
            {/* <ImageGrid
                images={[
                    {
                        url: parsedClub.imageUrl,
                        alt: parsedClub.name,
                    },
                ]}
            /> */}
        </div>
    );
};

export default ClubDetailHeader;
