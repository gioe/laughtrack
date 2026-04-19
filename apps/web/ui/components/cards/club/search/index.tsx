"use client";

import { motion } from "framer-motion";
import { MapPin } from "lucide-react";
import { useMotionProps } from "@/hooks";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ClubSearchCardProps {
    club: ClubDTO;
}

const ClubSearchCard: React.FC<ClubSearchCardProps> = ({ club }) => {
    const { mp } = useMotionProps();
    const parsedClub = new Club(club);
    const [error, setError] = useState(false);
    const locationLabel =
        parsedClub.city && parsedClub.state
            ? `${parsedClub.city}, ${parsedClub.state}`
            : parsedClub.city || parsedClub.address;

    return (
        <motion.div
            className="bg-gradient-to-b from-white to-coconut-cream/60 rounded-xl overflow-hidden pb-4 px-4 h-full shadow-sm border-b-2 border-transparent transition-all duration-300 hover:shadow-lg hover:border-copper"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
            <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-coconut-cream p-3">
                <Link
                    href={`/club/${parsedClub.name}`}
                    className="block w-full h-full"
                >
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={`${parsedClub.name}`}
                        fill
                        className="object-cover"
                        onError={() => setError(true)}
                        sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                        priority={false}
                    />
                </Link>
            </div>
            <div className="mt-4 space-y-2">
                <h2 className="text-h3 font-extrabold font-gilroy-bold text-center text-cedar hover:text-[#2D1810] transition-colors">
                    {parsedClub.name}
                </h2>

                <p className="text-body text-gray-600 text-center font-dmSans">
                    {locationLabel}
                </p>

                {club.chainName && (
                    <p className="text-xs text-gray-500 text-center font-dmSans">
                        {club.chainName}
                    </p>
                )}

                <div className="flex justify-center">
                    <span className="bg-copper/10 text-copper text-xs px-2 py-0.5 rounded-full font-dmSans">
                        {`${parsedClub.showCount ?? 0} upcoming shows`}
                    </span>
                </div>
                {club.distanceMiles != null && (
                    <p className="flex items-center justify-center gap-1 text-xs text-gray-500 font-dmSans">
                        <MapPin size={11} aria-hidden="true" />
                        {club.distanceMiles < 1
                            ? "< 1 mile away"
                            : `${Math.round(club.distanceMiles)} miles away`}
                    </p>
                )}
            </div>
        </motion.div>
    );
};

export default ClubSearchCard;
