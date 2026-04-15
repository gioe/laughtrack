"use client";

import React, { useState } from "react";
import { MapPin } from "lucide-react";
import Image from "next/image";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubDataColumn from "../social";
import { useMotionProps } from "@/hooks";
import { motion } from "framer-motion";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ClubDetailHeaderProps {
    club: ClubDTO;
}

const ClubDetailHeader: React.FC<ClubDetailHeaderProps> = ({ club }) => {
    const parsedClub = new Club(club);
    const { mv, mt, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const locationLabel =
        parsedClub.city && parsedClub.state
            ? `${parsedClub.city}, ${parsedClub.state}`
            : parsedClub.city || parsedClub.address;

    const showImage =
        !error && !!parsedClub.imageUrl && parsedClub.imageUrl !== PLACEHOLDER;

    return (
        <div className="max-w-7xl mx-auto">
            {/* Hero Image Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative w-full h-52 sm:h-64 md:h-80 overflow-hidden rounded-xl"
            >
                {/* Gradient fallback background */}
                <div className="absolute inset-0 bg-gradient-to-br from-stone-600 via-stone-800 to-stone-900" />

                {/* Hero image */}
                {showImage && (
                    <>
                        <Image
                            src={parsedClub.imageUrl}
                            alt={parsedClub.name}
                            fill
                            className={`object-cover object-center transition-opacity duration-500 ${
                                imageLoaded ? "opacity-100" : "opacity-0"
                            }`}
                            onError={() => setError(true)}
                            onLoad={() => setImageLoaded(true)}
                            priority
                            sizes="(max-width: 768px) 100vw, 1280px"
                        />
                        {/* Skeleton pulse during image load */}
                        {!imageLoaded && (
                            <div
                                className={`absolute inset-0 bg-stone-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                            />
                        )}
                        {/* Overlay gradient — only when image is present */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                    </>
                )}

                {/* Name + Address overlaid at bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-6">
                    <motion.h1
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.1) })}
                        className="text-3xl md:text-4xl font-bold text-white drop-shadow-lg mb-1"
                    >
                        {parsedClub.name}
                    </motion.h1>
                    {club.chainName && (
                        <motion.p
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.15),
                            })}
                            className="text-sm text-white/60 italic mb-1"
                        >
                            Part of the {club.chainName} family
                        </motion.p>
                    )}
                    <motion.div
                        initial={{ opacity: 0, y: mv(10) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.2) })}
                        className="flex items-center gap-2 text-white/80"
                    >
                        <MapPin aria-hidden="true" className="w-4 h-4" />
                        <span>{locationLabel}</span>
                    </motion.div>
                </div>
            </motion.div>

            {/* Contact info below hero */}
            <div className="p-6">
                <ClubDataColumn club={club} />
            </div>
        </div>
    );
};

export default ClubDetailHeader;
