"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Heart, Sparkles, Calendar, Users, Bell, Globe } from "lucide-react";
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

const compactNumber = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
});

interface HeaderStat {
    kind: "shows" | "followers";
    value: number;
    label: string;
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

function formatFollowerStat(totalFollowers: number) {
    return `${compactNumber.format(totalFollowers)} social followers`;
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

    const hasUpcomingShows = comedian.show_count > 0;

    const totalFollowers =
        (social?.instagram.following ?? 0) +
        (social?.tiktok.following ?? 0) +
        (social?.youtube.following ?? 0);

    const upcomingCityCount = getUpcomingCityCount(comedian);
    const stats: HeaderStat[] = [
        ...(comedian.show_count > 0
            ? [
                  {
                      kind: "shows" as const,
                      value: comedian.show_count,
                      label: formatUpcomingShowsStat(
                          comedian.show_count,
                          upcomingCityCount,
                      ),
                  },
              ]
            : []),
        ...(totalFollowers > 0
            ? [
                  {
                      kind: "followers" as const,
                      value: totalFollowers,
                      label: formatFollowerStat(totalFollowers),
                  },
              ]
            : []),
    ];
    const signatureStat = stats.reduce<HeaderStat | null>(
        (best, stat) => (!best || stat.value > best.value ? stat : best),
        null,
    );
    const secondaryStats = stats.filter(
        (stat) => stat.kind !== signatureStat?.kind,
    );

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
            "linear-gradient(135deg, rgba(54, 30, 20, 0.86) 0%, rgba(54, 30, 20, 0.74) 52%, var(--comedian-hero-accent-soft) 100%)",
    } as React.CSSProperties;

    const fallbackGradient = {
        backgroundImage:
            "linear-gradient(135deg, #361E14 0%, var(--comedian-hero-accent-soft) 48%, #361E14 100%)",
    } as React.CSSProperties;

    const imageBottomGradient = {
        backgroundImage:
            "linear-gradient(to top, #361E14 0%, rgba(54, 30, 20, 0.65) 45%, transparent 100%)",
    } as React.CSSProperties;

    const imageSideGradient = {
        backgroundImage:
            "linear-gradient(to right, #361E14 0%, rgba(54, 30, 20, 0.48) 54%, color-mix(in srgb, var(--comedian-hero-accent) 35%, transparent) 100%)",
    } as React.CSSProperties;

    const imageTopGradient = {
        backgroundImage:
            "linear-gradient(to bottom, rgba(54, 30, 20, 0.35) 0%, transparent 100%)",
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
                            className="object-cover object-center scale-110 blur-2xl opacity-60"
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
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
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
                        className="object-cover object-top"
                        onError={() => setError(true)}
                        onLoad={() => setImageLoaded(true)}
                        priority
                        sizes="100vw"
                    />
                    <div
                        className="absolute inset-0"
                        style={imageBottomGradient}
                    />
                    <div
                        className="absolute inset-0"
                        style={imageSideGradient}
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
                className="relative z-10 max-w-7xl mx-auto min-h-[28rem] md:min-h-[34rem] lg:min-h-[38rem] px-4 sm:px-6 lg:px-8 py-8 sm:py-10 md:py-12 lg:py-14 flex flex-col justify-end"
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
                        className="p-2.5 bg-white/75 backdrop-blur-sm rounded-full shadow-md hover:bg-white/90 hover:shadow-lg transition"
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

                <div className="w-full max-w-4xl text-center md:text-left lg:text-left">
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

                    {signatureStat && (
                        <motion.p
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.1),
                            })}
                            className="mt-3 text-lead font-dmSans text-white/75 drop-shadow"
                        >
                            {signatureStat.label}
                        </motion.p>
                    )}

                    {secondaryStats.length > 0 && (
                        <motion.ul
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.12),
                            })}
                            className="mt-2 flex flex-wrap justify-center md:justify-start lg:justify-start gap-x-4 gap-y-1 text-caption font-dmSans text-white/60 drop-shadow"
                        >
                            {secondaryStats.map((stat) => {
                                const Icon =
                                    stat.kind === "shows" ? Calendar : Users;

                                return (
                                    <li
                                        key={stat.kind}
                                        className="inline-flex items-center gap-1.5"
                                    >
                                        <Icon
                                            className="w-3.5 h-3.5"
                                            aria-hidden="true"
                                        />
                                        {stat.label}
                                    </li>
                                );
                            })}
                        </motion.ul>
                    )}

                    <motion.div
                        initial={{ opacity: 0, y: mv(10) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({
                            duration: 0.3,
                            delay: mv(0.15),
                        })}
                        className="mt-5 flex justify-center md:justify-start lg:justify-start"
                    >
                        {hasUpcomingShows ? (
                            <Button
                                asChild
                                variant="roundedShimmer"
                                className="min-h-12 gap-2 rounded-full bg-[var(--comedian-hero-cta)] px-7 py-3 text-base shadow-lg hover:bg-[var(--comedian-hero-cta-hover)]"
                            >
                                <a href="#comedian-upcoming-shows">
                                    <Calendar
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                    See next show
                                </a>
                            </Button>
                        ) : (
                            <Button
                                type="button"
                                variant="roundedShimmer"
                                onClick={handleNotifyClick}
                                disabled={isFavorite}
                                aria-pressed={isFavorite}
                                className="min-h-12 gap-2 rounded-full bg-[var(--comedian-hero-cta)] px-7 py-3 text-base shadow-lg hover:bg-[var(--comedian-hero-cta-hover)]"
                            >
                                <Bell className="h-5 w-5" aria-hidden="true" />
                                {isFavorite
                                    ? "Notifications on"
                                    : "Notify me about shows"}
                            </Button>
                        )}
                    </motion.div>

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
                                            className="inline-flex items-center gap-2 rounded-full bg-white/95 hover:bg-white text-cedar px-3 py-1.5 text-caption font-dmSans font-medium shadow-sm transition-colors"
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
