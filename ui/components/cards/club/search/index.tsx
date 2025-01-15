"use client";

import { Club } from "@/objects/class/club/Club";
import Image from "next/image";
import Link from "next/link";

interface ClubSearchCardProps {
    entity: string;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ entity }) => {
    const club = JSON.parse(entity) as Club;

    return (
        <div className="w-full rounded-xl overflow-hidden transition-transform duration-300 hover:scale-105">
            <div className="relative rounded-xl aspect-square">
                <Link
                    href={`/club/${club.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={club.cardImageUrl?.toString() ?? ""}
                        alt={club.name}
                        fill
                        className="object-cover rounded-xl"
                    />
                </Link>
            </div>
            <div className="p-4">
                <h2 className="text-xl font-bold mb-1">{club.name}</h2>
                <p className="text-gray-600">{club.address}</p>
            </div>
        </div>
    );
};

export default ClubSearchCard;
