"use client";

import { Club } from "@/objects/class/club/Club";
import Image from "next/image";

interface ClubSearchCardProps {
    entity: string;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ entity }) => {
    const club = JSON.parse(entity) as Club;

    return (
        <div className="w-[280px] rounded-xl overflow-hidden transition-transform duration-300 hover:scale-105">
            <div className="relative">
                <Image
                    src={club.cardImageUrl?.toString() ?? ""}
                    alt={club.name}
                    width={280}
                    height={280}
                    className="w-full object-cover"
                />
            </div>
            <div className="p-4">
                <h2 className="text-xl font-bold mb-1">{club.name}</h2>
                <p className="text-gray-600">{club.address}</p>
            </div>
        </div>
    );
};

export default ClubSearchCard;
