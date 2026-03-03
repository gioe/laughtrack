"use client";

import React, { useState } from "react";
import { MapPin } from "lucide-react";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubDataColumn from "../social";
import { getLocalCdnUrl } from "@/util/cdnUtil";

const PLACEHOLDER = getLocalCdnUrl("club-placeholder.png");

interface ClubDetailHeaderProps {
    club: ClubDTO;
}

const ClubDetailHeader: React.FC<ClubDetailHeaderProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const [error, setError] = useState(false);

    return (
        <div className="max-w-7xl mx-auto p-6">
            {/* Header Section */}
            <div className="w-full  p-4">
                <div className="flex items-center justify-between max-w-6xl mx-auto">
                    <div className="flex items-center gap-4">
                        <img
                            src={error ? PLACEHOLDER : parsedClub.imageUrl}
                            alt={parsedClub.name}
                            onError={() => setError(true)}
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
            <ClubDataColumn club={club} />
        </div>
    );
};

export default ClubDetailHeader;
