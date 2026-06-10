"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { MapPin, Ticket } from "lucide-react";
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

// Marquee hero ported from the iOS composition (ios MarqueeHero.swift):
// copper venue eyebrow above an uppercase title above a square poster framed
// by a dashed copper ring. iOS reference values — 11pt eyebrow with 2.2
// tracking in accentStrong, 196pt poster, dashed accentStrong ring with a
// copper glow, scaledToFill poster crop.
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
                className="relative w-full overflow-hidden rounded-xl bg-surface px-6 py-8 sm:py-10"
            >
                {/* Radial copper glow behind the poster, the web analogue of the
                    iOS marquee's accent RadialGradient over heroStart. */}
                <div
                    aria-hidden="true"
                    className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_theme(colors.accent-strong/16%),_transparent_65%)]"
                />

                <div className="relative flex flex-col items-center gap-4 text-center">
                    {show.clubName && (
                        <Link
                            href={`/club/${show.clubName}`}
                            className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-strong font-dmSans underline-offset-4 hover:underline focus-visible:underline"
                        >
                            {show.clubName}
                        </Link>
                    )}

                    {/* sm/md are bounded ranges in this config, so lg must be
                        chained explicitly for the size to hold at ≥1200px. */}
                    <h1 className="max-w-3xl text-2xl sm:text-3xl md:text-4xl lg:text-4xl font-urbanist-bold font-bold uppercase tracking-wide text-white drop-shadow-md">
                        {heading}
                    </h1>

                    {/* Square poster framed by a dashed copper ring. */}
                    <div
                        data-testid="marquee-poster-frame"
                        className="relative mt-2 rounded-[14px] border-2 border-dashed border-accent-strong p-[5px] shadow-[0_0_14px_theme(colors.accent-strong/45%)]"
                    >
                        <div className="relative size-40 sm:size-[196px] md:size-[196px] lg:size-[196px] overflow-hidden rounded-[10px]">
                            {showImage ? (
                                <>
                                    <Image
                                        src={show.imageUrl}
                                        alt={show.clubName ?? "Club"}
                                        fill
                                        className={`object-cover object-center transition-opacity duration-500 ${
                                            imageLoaded
                                                ? "opacity-100"
                                                : "opacity-0"
                                        }`}
                                        onError={() => setError(true)}
                                        onLoad={() => setImageLoaded(true)}
                                        priority
                                        sizes="196px"
                                    />
                                    {!imageLoaded && (
                                        <div
                                            className={`absolute inset-0 bg-surface-elevated${!prefersReducedMotion ? " animate-pulse" : ""}`}
                                        />
                                    )}
                                </>
                            ) : (
                                <div
                                    data-testid="marquee-poster-fallback"
                                    className="flex h-full w-full items-center justify-center bg-surface-muted"
                                >
                                    <Ticket
                                        size={64}
                                        className="text-accent-strong"
                                        aria-hidden="true"
                                    />
                                </div>
                            )}
                        </div>
                    </div>

                    <span
                        className={`inline-block text-caption font-bold uppercase tracking-wider text-white px-2.5 py-1 rounded-full font-dmSans ${COUNTDOWN_TONE_CLASSES[countdown.tone]}`}
                        aria-live={countdown.tone === "live" ? "polite" : "off"}
                    >
                        {countdown.label}
                    </span>
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
