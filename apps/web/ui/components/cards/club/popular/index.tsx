"use client";

import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface PopularClubCardProps {
    entity: ClubDTO;
}

const PopularClubCard: React.FC<PopularClubCardProps> = ({ entity }) => {
    const { mp } = useMotionProps();
    const club = new Club(entity);
    const [error, setError] = useState(false);

    return (
        <motion.div
            className="w-full"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
            <div className="relative w-full aspect-square rounded-xl overflow-hidden mb-4 hover:cursor-pointer">
                <Link
                    href={`/club/${club.name}`}
                    className="block w-full h-full relative"
                >
                    <Image
                        src={error ? PLACEHOLDER : club.imageUrl}
                        alt={club.name}
                        fill
                        className="object-cover"
                        onError={() => setError(true)}
                        sizes="(max-width: 319px) calc(100vw - 2rem), (max-width: 640px) 280px, 320px"
                        priority={false}
                    />
                </Link>
            </div>

            {/* Text Content */}
            <div className="space-y-1">
                <h2 className="text-[21px] font-bold leading-tight font-gilroy-bold">
                    {club.name}
                </h2>
                <p className="text-[16px] text-gray-600 font-dmSans">
                    {club.activeComedianCount} active comedians
                </p>
            </div>
        </motion.div>
    );
};

export default PopularClubCard;
