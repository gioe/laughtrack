"use client";

import { Club } from "@/objects/class/club/Club";
import ClubMarquee from "../../../image/club";

interface ClubCarouselCardProps {
    entity: string;
}

const ClubCarouselCard: React.FC<ClubCarouselCardProps> = ({ entity }) => {
    const club = JSON.parse(entity) as Club;

    return (
        <div className="min-w-[300px] flex-shrink-0 snap-start">
            <div className="bg-black rounded-lg overflow-hidden aspect-square mb-4 relative">
                <ClubMarquee priority club={club} tooltip={false} />
            </div>
            <h3 className="text-xl font-bold text-[#2D1810]">
                {club.name}
                {club.address && (
                    <span className="block text-lg font-normal">
                        {club.address}
                    </span>
                )}
            </h3>
            <p className="text-gray-600 mt-1">{`${club.activeComedianCount} active comedians`}</p>
        </div>
    );
};

export default ClubCarouselCard;
