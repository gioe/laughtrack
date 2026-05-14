"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { MapPin } from "lucide-react";
import { useMotionProps } from "@/hooks";
import { formatShowCountdown, formatShowDate } from "@/util/dateUtil";
import { ShowDetailDTO } from "@/lib/data/show/detail/interface";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

interface ShowDetailHeaderProps {
    show: ShowDetailDTO;
}

// Tailwind background for each countdown tone — kept literal so the JIT picks them up.
const COUNTDOWN_TONE_CLASSES: Record<string, string> = {
    future: "bg-copper/90",
    live: "bg-emerald-600/90",
    past: "bg-stone-600/90",
};

const ShowDetailHeader: React.FC<ShowDetailHeaderProps> = ({ show }) => {
    const { mt, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    // Re-derive the countdown every minute so future→live→past transitions
    // fire without a page reload (a user who lands 4 minutes before showtime
    // otherwise sees the label frozen as the show starts).
    const [now, setNow] = useState<Date>(() => new Date());
    useEffect(() => {
        const interval = setInterval(() => setNow(new Date()), 60_000);
        return () => clearInterval(interval);
    }, []);
    const showImage = !error && show.imageUrl && show.imageUrl !== PLACEHOLDER;
    const heading =
        show.name && show.name.trim()
            ? show.name
            : `Comedy at ${show.clubName ?? ""}`;
    const dateLabel = formatShowDate(show.date.toString(), show.timezone);
    const countdown = formatShowCountdown(show.date.toString(), now);

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
                    <span
                        className={`inline-block mb-3 text-caption font-bold uppercase tracking-wider text-white px-2.5 py-1 rounded-full font-dmSans ${COUNTDOWN_TONE_CLASSES[countdown.tone]}`}
                        aria-live={countdown.tone === "live" ? "polite" : "off"}
                    >
                        {countdown.label}
                    </span>
                    <h1 className="text-2xl sm:text-3xl md:text-4xl font-gilroy-bold font-bold text-white drop-shadow-md">
                        {heading}
                    </h1>
                    {show.clubName && (
                        <p className="mt-2 text-base sm:text-lg text-white/90 font-dmSans">
                            at{" "}
                            <Link
                                href={`/club/${show.clubName}`}
                                className="underline-offset-2 hover:underline focus-visible:underline"
                            >
                                {show.clubName}
                            </Link>
                        </p>
                    )}
                </div>
            </motion.div>

            <div className="mt-4 sm:mt-6 text-base sm:text-lg text-foreground font-dmSans">
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
