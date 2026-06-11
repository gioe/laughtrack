"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { cn } from "@/util/tailwindUtil";

interface MarqueeHeroProps {
    title: string;
    eyebrow?: React.ReactNode;
    imageSrc?: string | null;
    imageAlt: string;
    fallback: React.ReactNode;
    children?: React.ReactNode;
    className?: string;
    posterClassName?: string;
    imageClassName?: string;
    priority?: boolean;
}

// Wide-wordmark exception to the square cover crop (TASK-2787): club images
// at or beyond this width:height ratio letterbox with object-contain on
// surface-muted instead of cover-cropping. A 2026-06 survey of all 192 club
// CDN PNGs found 34% are >=2:1 and visually those are wordmark logos
// (Goodnights 3.8:1 cover-crops to an illegible "ODNIG / MEDY C"), while the
// 1.5-2:1 band is venue photos that center-crop fine. Below the threshold,
// the iOS-matching cover crop (TASK-2767) still applies.
const LOGO_ASPECT_THRESHOLD = 2;

// Shared web port of the iOS MarqueeHero. Artwork is deliberately forced into
// a square poster: most source images are square-ish, and the dashed
// accent-strong ring is the marquee-light treatment that makes uneven source
// crops feel intentional instead of like arbitrary rectangles.
export default function MarqueeHero({
    title,
    eyebrow,
    imageSrc,
    imageAlt,
    fallback,
    children,
    className,
    posterClassName,
    imageClassName,
    priority = true,
}: MarqueeHeroProps) {
    const { springs, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [letterboxImage, setLetterboxImage] = useState(false);
    const showImage = Boolean(imageSrc) && !error;

    useEffect(() => {
        setError(false);
        setImageLoaded(false);
        setLetterboxImage(false);
    }, [imageSrc]);

    return (
        <div className="max-w-7xl mx-auto">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={springs.contentEntrance}
                className={cn(
                    "relative w-full overflow-hidden rounded-xl bg-surface px-6 py-8 sm:py-10",
                    className,
                )}
            >
                <div
                    aria-hidden="true"
                    className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_theme(colors.accent-strong/16%),_transparent_65%)]"
                />

                <div className="relative flex flex-col items-center gap-4 text-center">
                    {eyebrow ? (
                        <div className="text-caption font-semibold uppercase tracking-[0.2em] text-accent-strong font-dmSans">
                            {eyebrow}
                        </div>
                    ) : null}

                    {/* sm/md are bounded ranges in this config, so lg must be
                        chained explicitly for the size to hold at >=1200px. */}
                    <h1 className="max-w-3xl text-2xl sm:text-3xl md:text-4xl lg:text-4xl font-urbanist-bold font-bold uppercase tracking-wide text-white drop-shadow-md">
                        {title}
                    </h1>

                    <div
                        data-testid="marquee-poster-frame"
                        className="relative mt-2 rounded-[14px] border-2 border-dashed border-accent-strong p-[5px] shadow-[0_0_14px_theme(colors.accent-strong/45%)]"
                    >
                        <div
                            className={cn(
                                "relative size-40 sm:size-[196px] md:size-[196px] lg:size-[196px] overflow-hidden rounded-[10px]",
                                letterboxImage && "bg-surface-muted",
                                posterClassName,
                            )}
                        >
                            {showImage ? (
                                <>
                                    <Image
                                        src={imageSrc as string}
                                        alt={imageAlt}
                                        fill
                                        className={cn(
                                            "object-center transition-opacity duration-500",
                                            letterboxImage
                                                ? "object-contain p-3"
                                                : "object-cover",
                                            imageLoaded
                                                ? "opacity-100"
                                                : "opacity-0",
                                            imageClassName,
                                        )}
                                        onError={() => setError(true)}
                                        onLoad={(event) => {
                                            const image = event.currentTarget;
                                            setLetterboxImage(
                                                image.naturalHeight > 0 &&
                                                    image.naturalWidth /
                                                        image.naturalHeight >=
                                                        LOGO_ASPECT_THRESHOLD,
                                            );
                                            setImageLoaded(true);
                                        }}
                                        priority={priority}
                                        sizes="196px"
                                    />
                                    {!imageLoaded && (
                                        <div
                                            className={cn(
                                                "absolute inset-0 bg-surface-elevated",
                                                !prefersReducedMotion &&
                                                    "animate-pulse",
                                            )}
                                        />
                                    )}
                                </>
                            ) : (
                                <div
                                    data-testid="marquee-poster-fallback"
                                    className="h-full w-full"
                                >
                                    {fallback}
                                </div>
                            )}
                        </div>
                    </div>

                    {children}
                </div>
            </motion.div>
        </div>
    );
}
