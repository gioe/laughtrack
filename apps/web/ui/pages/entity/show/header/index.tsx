"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { MapPin } from "lucide-react";
import { useMotionProps } from "@/hooks";
import { formatShowDate } from "@/util/dateUtil";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ShowDetailHeaderProps {
    show: ShowDetailDTO;
}

const ShowDetailHeader: React.FC<ShowDetailHeaderProps> = ({ show }) => {
    const { mt, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const showImage = !error && show.imageUrl && show.imageUrl !== PLACEHOLDER;
    const heading =
        show.name && show.name.trim()
            ? show.name
            : `Comedy at ${show.clubName ?? ""}`;
    const dateLabel = formatShowDate(show.date.toString(), show.timezone);

    return (
        <div className="max-w-7xl mx-auto">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative w-full h-52 sm:h-64 md:h-80 overflow-hidden rounded-xl"
            >
                <div className="absolute inset-0 bg-gradient-to-br from-stone-600 via-stone-800 to-stone-900" />

                {showImage && (
                    <>
                        <Image
                            src={show.imageUrl}
                            alt={show.clubName ?? "Club"}
                            fill
                            className={`object-cover object-center transition-opacity duration-500 ${
                                imageLoaded ? "opacity-100" : "opacity-0"
                            }`}
                            onError={() => setError(true)}
                            onLoad={() => setImageLoaded(true)}
                            priority
                            sizes="(max-width: 768px) 100vw, 1280px"
                        />
                        {!imageLoaded && (
                            <div
                                className={`absolute inset-0 bg-stone-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                            />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                    </>
                )}

                <div className="absolute bottom-0 left-0 right-0 p-6">
                    {show.isPast && (
                        <span className="inline-block mb-3 text-[11px] font-bold uppercase tracking-wider text-white bg-stone-600/90 px-2.5 py-1 rounded-full font-dmSans">
                            Archived
                        </span>
                    )}
                    <h1 className="text-2xl sm:text-3xl md:text-4xl font-gilroy-bold font-bold text-white drop-shadow-md">
                        {heading}
                    </h1>
                    {show.clubName && (
                        <p className="mt-2 text-base sm:text-lg text-white/90 font-dmSans">
                            at{" "}
                            <Link
                                href={`/club/${show.clubSlug}`}
                                className="underline-offset-2 hover:underline focus-visible:underline"
                            >
                                {show.clubName}
                            </Link>
                        </p>
                    )}
                </div>
            </motion.div>

            <div className="mt-4 sm:mt-6 text-base sm:text-lg text-cedar font-dmSans">
                <p>{dateLabel}</p>
                {show.room && (
                    <p className="text-sm text-gray-600 mt-1">{show.room}</p>
                )}
                {show.address && (
                    <p className="flex items-center gap-1 text-sm text-gray-600 mt-1">
                        <MapPin size={14} aria-hidden="true" />
                        {show.address}
                    </p>
                )}
            </div>
        </div>
    );
};

export default ShowDetailHeader;
