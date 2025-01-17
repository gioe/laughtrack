"use client";

import React, { useState } from "react";
import { MapPin } from "lucide-react";
import ImageGrid from "@/ui/components/grid/image";
import { Club } from "@/objects/class/club/Club";

interface ClubDetailHeaderProps {
    clubString: string;
}

const ClubDetailHeader: React.FC<ClubDetailHeaderProps> = ({ clubString }) => {
    const club = JSON.parse(clubString) as Club;
    const [isLoading, setIsLoading] = useState(false);

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header Section */}
            <div className="w-full bg-cream-50 p-4">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                    <div className="flex items-center gap-4">
                        <img
                            src={club.imageUrl}
                            alt={`${club.name} logo`}
                            className="w-16 h-16 rounded-full"
                        />
                        <div className="flex flex-col gap-1">
                            <h1 className="text-2xl font-bold text-gray-900">
                                {club.name}
                            </h1>
                            <div className="flex items-center gap-2 text-gray-600">
                                <MapPin className="w-4 h-4" />
                                <span>{club.address}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Image Grid */}
            <ImageGrid images={[]} />
        </div>
    );
};

export default ClubDetailHeader;
