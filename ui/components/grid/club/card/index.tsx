"use client";

import { Club } from "@/objects/class/club/Club";
import ClubMarquee from "../../../image/club";
import Image from "next/image";

interface ClubCarouselCardProps {
    entity: string;
}

const ClubCarouselCard: React.FC<ClubCarouselCardProps> = ({ entity }) => {
    const club = JSON.parse(entity) as Club;

    return (
        <div className="w-[218px]">
            {/* Image Container */}
            <div className="relative w-[218px] h-[218px] rounded-2xl overflow-hidden mb-4">
                <Image
                    src={club.cardImageUrl?.toString() ?? ""}
                    alt={club.name}
                    width={218}
                    height={218}
                    className="object-cover"
                    priority
                />
            </div>

            {/* Text Content */}
            <div className="space-y-1">
                <h2 className="text-[21px] font-bold leading-tight font-outfit">
                    {club.name}
                </h2>
                <p className="text-[16px] text-gray-600 font-dmSans">
                    {club.activeComedianCount} active comedians
                </p>
            </div>
        </div>
    );
};

export default ClubCarouselCard;
