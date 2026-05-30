"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Heart, Sparkles, Bell, Globe } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { useFavorite } from "@/hooks/useFavorite";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps } from "@/hooks";
import Image from "next/image";
import ComedianAvatarFallback from "@/ui/components/image/comedian/fallback";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import YouTubeIcon from "@/ui/components/icons/YouTubeIcon";
import { Button } from "@/ui/components/ui/button";
import {
    COMEDIAN_HERO_DEFAULTS,
    ComedianHeroPalette,
} from "@/lib/data/comedian/detail/heroPalette";

interface ComedianDetailHeaderProps {
    comedian: ComedianDTO;
    heroPalette?: ComedianHeroPalette | null;
}

function getUpcomingCityCount(comedian: ComedianDTO) {
    const cities = new Set(
        (comedian.dates ?? [])
            .map((show) => {
                const city = show.clubCity?.trim();
                if (!city) return null;
                const state = show.clubState?.trim();
                return state ? `${city}, ${state}` : city;
            })
            .filter(Boolean),
    );

    return cities.size;
}

function formatUpcomingShowsStat(showCount: number, cityCount: number) {
    const showText = `${showCount.toLocaleString()} upcoming ${
        showCount === 1 ? "show" : "shows"
    }`;

    if (cityCount === 0) return showText;

    return `${showText} in ${cityCount.toLocaleString()} ${
        cityCount === 1 ? "city" : "cities"
    }`;
}

const ComedianDetailHeader: React.FC<ComedianDetailHeaderProps> = ({
    comedian,
    heroPalette,
}) => {
    const { mv, mp, mt, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [showConfetti, setShowConfetti] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const showImage = !error && !!comedian.imageUrl;

    useEffect(() => {
        setImageLoaded(false);
        if (imageRef.current?.complete && showImage) {
            setImageLoaded(true);
        }
    }, [comedian.imageUrl, showImage]);

    const parsedComedian = new Comedian(comedian);
    const social = parsedComedian.socialData;

    const { isFavorite, handleFavoriteClick } = useFavorite({
        initialState: parsedComedian.isFavorite ?? false,
        entityId: comedian.uuid,
    });

    const handleFavoriteWithAnimation = async (e: React.MouseEvent) => {
        if (!isFavorite) {
            setShowConfetti(true);
            setTimeout(() => setShowConfetti(false), 2000);
        }
        await handleFavoriteClick(e);
    };

    const handleNotifyClick = async (e: React.MouseEvent) => {
        if (isFavorite) return;
        await handleFavoriteWithAnimation(e);
    };

    const hasUpcomingShows = comedian.showCount > 0;

    const upcomingShowsLabel = hasUpcomingShows
        ? formatUpcomingShowsStat(
              comedian.showCount,
              getUpcomingCityCount(comedian),
          )
        : null;

    const socialLinks = useMemo(() => {
        const stripAt = (s: string | null | undefined) =>
            s ? s.replace(/^@+/, "") : s;
        const ig = stripAt(social?.instagram.account);
        const tt = stripAt(social?.tiktok.account);
        const yt = stripAt(social?.youtube.account);

        return [
            {
                platform: "Instagram",
                account: ig,
                href: `https://instagram.com/${ig}`,
                Icon: InstagramIcon,
            },
            {
                platform: "TikTok",
                account: tt,
                href: `https://tiktok.com/@${tt}`,
                Icon: TikTokIcon,
            },
            {
                platform: "YouTube",
                account: yt,
                href: `https://youtube.com/@${yt}`,
                Icon: YouTubeIcon,
            },
            {
                platform: "Website",
                account: social?.website,
                href: social?.website
                    ? social.website.startsWith("http://") ||
                      social.website.startsWith("https://")
                        ? social.website
                        : `https://${social.website}`
                    : "#",
                Icon: Globe,
            },
        ].filter((link) => Boolean(link.account));
    }, [social]);

    const palette = heroPalette ?? COMEDIAN_HERO_DEFAULTS;
    const heroStyle = {
        "--comedian-hero-accent": palette.accent,
        "--comedian-hero-accent-soft": palette.accentSoft,
        "--comedian-hero-cta": palette.cta,
        "--comedian-hero-cta-hover": palette.ctaHover,
    } as React.CSSProperties;

    const backdropGradient = {
        backgroundImage:
            "linear-gradient(135deg, rgba(30, 18, 12, 0.92) 0%, rgba(54, 30, 20, 0.74) 44%, var(--comedian-hero-accent-soft) 100%)",
    } as React.CSSProperties;

    const fallbackGradient = {
        backgroundImage:
            "linear-gradient(135deg, #1f120c 0%, #361E14 42%, var(--comedian-hero-accent-soft) 100%)",
    } as React.CSSProperties;

    const imageBottomGradient = {
        backgroundImage:
            "linear-gradient(to top, rgba(18, 12, 8, 0.52) 0%, rgba(18, 12, 8, 0.18) 38%, transparent 72%)",
    } as React.CSSProperties;

    const imageLeftGradient = {
        backgroundImage:
            "linear-gradient(to right, #1f120c 0%, rgba(31, 18, 12, 0.92) 28%, rgba(31, 18, 12, 0.48) 56%, transparent 82%)",
    } as React.CSSProperties;

    const imageTopGradient = {
        backgroundImage:
            "linear-gradient(to bottom, rgba(18, 12, 8, 0.32) 0%, transparent 42%)",
    } as React.CSSProperties;

    const portraitGlow = {
        backgroundImage:
            "radial-gradient(circle at 74% 44%, rgba(255, 236, 205, 0.18) 0%, rgba(255, 236, 205, 0.08) 28%, transparent 58%)",
    } as React.CSSProperties;

    return (
        <section
            className="relative w-full overflow-hidden bg-cedar"
            style={heroStyle}
        >
            {/* Blurred backdrop (uses headshot when present, else warm gradient) */}
            <div className="absolute inset-0">
                {showImage ? (
                    <>
                        <Image
                            src={comedian.imageUrl}
                            alt=""
                            aria-hidden="true"
                            fill
                            className="object-cover object-center scale-110 blur-2xl opacity-45"
                            sizes="100vw"
                            priority
                        />
                        <div
                            className="absolute inset-0"
                            style={backdropGradient}
                        />
                    </>
                ) : (
                    <div
                        className="absolute inset-0"
                        style={fallbackGradient}
                    />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/35 via-transparent to-transparent" />
            </div>

            {showImage && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: imageLoaded ? 1 : 0 }}
                    transition={mt({ duration: 0.5 })}
                    className="absolute inset-0 z-0"
                >
                    <Image
                        ref={imageRef}
                        src={comedian.imageUrl}
                        alt={parsedComedian.name}
                        fill
                        className="object-contain object-top md:object-right-top lg:object-right"
                        onError={() => setError(true)}
                        onLoad={() => setImageLoaded(true)}
                        priority
                        sizes="100vw"
                    />
                    <div className="absolute inset-0" style={portraitGlow} />
                    <div
                        className="absolute inset-0"
                        style={imageBottomGradient}
                    />
                    <div
                        className="absolute inset-0"
                        style={imageLeftGradient}
                    />
                    <div
                        className="absolute inset-0"
                        style={imageTopGradient}
                    />
                </motion.div>
            )}

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative z-10 max-w-7xl mx-auto min-h-[30rem] md:min-h-[34rem] lg:min-h-[38rem] px-4 sm:px-6 lg:px-8 py-8 sm:py-10 md:py-12 lg:py-14 flex flex-col justify-end"
            >
                {/* Favorite button — pinned to top-right of the hero */}
                <motion.div
                    whileHover={mp({ scale: 1.1 })}
                    whileTap={mp({ scale: 0.9 })}
                    className="absolute top-4 right-4 sm:top-6 sm:right-6 z-20"
                >
                    <button
                        onClick={handleFavoriteWithAnimation}
                        aria-label={
                            isFavorite
                                ? "Remove from favorites"
                                : "Add to favorites"
                        }
                        aria-pressed={isFavorite}
                        className="p-2.5 bg-[#FAF6E0]/95 text-[#24160f] backdrop-blur-sm rounded-full shadow-md ring-1 ring-black/10 hover:bg-white hover:shadow-lg transition"
                    >
                        <Heart
                            aria-hidden="true"
                            className={`w-5 h-5 ${
                                isFavorite
                                    ? "text-red-500 fill-current"
                                    : "text-gray-700"
                            }`}
                        />
                    </button>
                </motion.div>

                <div className="w-full max-w-3xl text-center md:text-left lg:text-left">
                    {!showImage && (
                        /* Fallback remains contained only when no usable hero headshot exists. */
                        <div className="mx-auto md:mx-0 mb-6 relative h-44 w-44 sm:h-56 sm:w-56 rounded-2xl overflow-hidden ring-4 ring-white/20 shadow-2xl">
                            <ComedianAvatarFallback
                                name={parsedComedian.name}
                                variant="hero"
                            />
                        </div>
                    )}

                    <motion.div
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.05) })}
                        className="max-w-4xl"
                    >
                        <h1 className="text-h1 sm:text-display md:text-display lg:text-hero font-chivo font-bold text-white drop-shadow-md leading-tight">
                            {parsedComedian.name}
                        </h1>
                    </motion.div>

                    {upcomingShowsLabel && (
                        <motion.p
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.1),
                            })}
                            className="mt-3 text-lead font-dmSans text-white/75 drop-shadow"
                        >
                            {upcomingShowsLabel}
                        </motion.p>
                    )}

                    {!hasUpcomingShows && (
                        <motion.div
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.15),
                            })}
                            className="mt-5 flex justify-center md:justify-start lg:justify-start"
                        >
                            <Button
                                type="button"
                                variant="roundedShimmer"
                                onClick={handleNotifyClick}
                                disabled={isFavorite}
                                aria-pressed={isFavorite}
                                className="min-h-12 gap-2 rounded-full border border-white/20 bg-[#FAF6E0] px-7 py-3 text-base text-[#24160f] shadow-lg shadow-black/25 hover:bg-white"
                            >
                                <Bell className="h-5 w-5" aria-hidden="true" />
                                {isFavorite
                                    ? "Notifications on"
                                    : "Notify me about shows"}
                            </Button>
                        </motion.div>
                    )}

                    {/* Bio */}
                    {comedian.bio && (
                        <motion.p
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.15),
                            })}
                            className="mt-4 text-lead font-dmSans text-white/90 whitespace-pre-line max-w-2xl mx-auto md:mx-0 lg:mx-0 drop-shadow"
                        >
                            {comedian.bio}
                        </motion.p>
                    )}

                    {/* Social row */}
                    {socialLinks.length > 0 && (
                        <motion.ul
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.2),
                            })}
                            className="mt-5 flex flex-wrap justify-center md:justify-start lg:justify-start gap-2"
                        >
                            {socialLinks.map((link) => {
                                const { Icon, platform, account, href } = link;
                                return (
                                    <li key={platform}>
                                        <a
                                            href={href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            aria-label={`${parsedComedian.name} on ${platform}`}
                                            className="inline-flex items-center gap-2 rounded-full bg-[#FAF6E0]/95 hover:bg-white text-[#24160f] px-3 py-1.5 text-caption font-dmSans font-semibold shadow-sm shadow-black/20 ring-1 ring-black/10 transition-colors"
                                        >
                                            <Icon
                                                className="w-4 h-4"
                                                aria-hidden="true"
                                            />
                                            <span className="truncate max-w-[10rem]">
                                                {platform === "Website"
                                                    ? platform
                                                    : `@${account}`}
                                            </span>
                                        </a>
                                    </li>
                                );
                            })}
                        </motion.ul>
                    )}
                </div>

                {showImage && !imageLoaded && (
                    <div
                        className={`absolute inset-0 -z-10 bg-cedar${!prefersReducedMotion ? " animate-pulse" : ""}`}
                    />
                )}

                {/* Confetti burst */}
                <AnimatePresence>
                    {showConfetti && (
                        <motion.div
                            initial={{ opacity: mv(0, 1), scale: mv(0, 1) }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: mv(0, 1), scale: mv(0, 1) }}
                            transition={
                                prefersReducedMotion
                                    ? { duration: 0 }
                                    : undefined
                            }
                            className="absolute inset-0 flex items-center justify-center pointer-events-none"
                        >
                            <Sparkles
                                aria-hidden="true"
                                className="w-12 h-12 text-yellow-400"
                            />
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </section>
    );
};

export default ComedianDetailHeader;
