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

interface ComedianDetailHeaderProps {
    comedian: ComedianDTO;
}

const compactNumber = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
});

const ComedianDetailHeader: React.FC<ComedianDetailHeaderProps> = ({
    comedian,
}) => {
    const { mv, mp, mt, prefersReducedMotion } = useMotionProps();
    const [error, setError] = useState(false);
    const [showConfetti, setShowConfetti] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const imageRef = useRef<HTMLImageElement | null>(null);

    useEffect(() => {
        if (imageRef.current?.complete) {
            setImageLoaded(true);
        }
    }, [comedian.imageUrl]);

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

    const showImage = !error && !!comedian.imageUrl;
    const hasUpcomingShows = comedian.show_count > 0;

    const totalFollowers =
        (social?.instagram.following ?? 0) +
        (social?.tiktok.following ?? 0) +
        (social?.youtube.following ?? 0);

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

    return (
        <section className="relative w-full overflow-hidden bg-cedar">
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
                        <div className="absolute inset-0 bg-gradient-to-br from-cedar/80 via-cedar/70 to-paarl/50" />
                    </>
                ) : (
                    <div className="absolute inset-0 bg-gradient-to-br from-cedar via-paarl/40 to-cedar" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 md:py-12 lg:py-14"
            >
                {/* Favorite button — pinned to top-right of the hero */}
                <motion.div
                    whileHover={mp({ scale: 1.1 })}
                    whileTap={mp({ scale: 0.9 })}
                    className="absolute top-4 right-4 sm:top-6 sm:right-6"
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

                <div className="flex flex-col md:flex-row lg:flex-row items-center md:items-stretch lg:items-stretch gap-6 md:gap-8 lg:gap-10">
                    {/* Headshot */}
                    <motion.div
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.4 })}
                        className="relative flex-shrink-0 w-44 h-44 sm:w-56 sm:h-56 md:w-64 md:h-64 lg:w-72 lg:h-72 rounded-2xl overflow-hidden ring-4 ring-white/20 shadow-2xl"
                    >
                        {showImage ? (
                            <>
                                <div className="absolute inset-0 bg-gradient-to-br from-slate-600 via-slate-800 to-slate-900" />
                                <Image
                                    ref={imageRef}
                                    src={comedian.imageUrl}
                                    alt={parsedComedian.name}
                                    fill
                                    className={`object-cover object-top transition-opacity duration-500 ${
                                        imageLoaded
                                            ? "opacity-100"
                                            : "opacity-0"
                                    }`}
                                    onError={() => setError(true)}
                                    onLoad={() => setImageLoaded(true)}
                                    priority
                                    sizes="(max-width: 768px) 240px, 288px"
                                />
                                {!imageLoaded && (
                                    <div
                                        className={`absolute inset-0 bg-slate-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                                    />
                                )}
                            </>
                        ) : (
                            <div className="absolute inset-0">
                                <ComedianAvatarFallback
                                    name={parsedComedian.name}
                                    variant="hero"
                                />
                            </div>
                        )}
                    </motion.div>

                    {/* Info column */}
                    <div className="flex-1 min-w-0 flex flex-col justify-center text-center md:text-left lg:text-left">
                        <motion.h1
                            initial={{ opacity: 0, y: mv(20) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({ duration: 0.3, delay: mv(0.05) })}
                            className="text-h1 sm:text-display md:text-display lg:text-hero font-chivo font-bold text-white drop-shadow-md leading-tight"
                        >
                            {parsedComedian.name}
                        </motion.h1>

                        {/* Stats chips */}
                        {(comedian.show_count > 0 || totalFollowers > 0) && (
                            <motion.ul
                                initial={{ opacity: 0, y: mv(10) }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={mt({
                                    duration: 0.3,
                                    delay: mv(0.1),
                                })}
                                className="mt-3 flex flex-wrap justify-center md:justify-start lg:justify-start gap-2"
                            >
                                {comedian.show_count > 0 && (
                                    <li className="inline-flex items-center gap-1.5 rounded-full bg-white/15 backdrop-blur-sm border border-white/20 px-3 py-1 text-caption font-dmSans text-white">
                                        <Calendar
                                            className="w-3.5 h-3.5"
                                            aria-hidden="true"
                                        />
                                        {comedian.show_count.toLocaleString()}{" "}
                                        upcoming{" "}
                                        {comedian.show_count === 1
                                            ? "show"
                                            : "shows"}
                                    </li>
                                )}
                                {totalFollowers > 0 && (
                                    <li className="inline-flex items-center gap-1.5 rounded-full bg-white/15 backdrop-blur-sm border border-white/20 px-3 py-1 text-caption font-dmSans text-white">
                                        <Users
                                            className="w-3.5 h-3.5"
                                            aria-hidden="true"
                                        />
                                        {compactNumber.format(totalFollowers)}{" "}
                                        followers
                                    </li>
                                )}
                            </motion.ul>
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
                                className="mt-4 text-lead font-dmSans text-white/90 whitespace-pre-line max-w-2xl mx-auto md:mx-0 lg:mx-0"
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
                                    const { Icon, platform, account, href } =
                                        link;
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

                        <motion.div
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={mt({
                                duration: 0.3,
                                delay: mv(0.25),
                            })}
                            className="mt-6 flex justify-center md:justify-start lg:justify-start"
                        >
                            {hasUpcomingShows ? (
                                <Button
                                    asChild
                                    variant="roundedShimmer"
                                    className="min-h-12 gap-2 rounded-full px-7 py-3 text-base shadow-lg"
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
                                    className="min-h-12 gap-2 rounded-full px-7 py-3 text-base shadow-lg"
                                >
                                    <Bell
                                        className="h-5 w-5"
                                        aria-hidden="true"
                                    />
                                    {isFavorite
                                        ? "Notifications on"
                                        : "Notify me about shows"}
                                </Button>
                            )}
                        </motion.div>
                    </div>
                </div>

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
