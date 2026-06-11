"use client";

import React, { useMemo, useState } from "react";
import { Heart, Sparkles, Bell, Globe } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { useFavorite } from "@/hooks/useFavorite";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps, MOTION_TAP_SCALE } from "@/hooks";
import ComedianAvatarFallback from "@/ui/components/image/comedian/fallback";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import YouTubeIcon from "@/ui/components/icons/YouTubeIcon";
import { Button } from "@/ui/components/ui/button";
import MarqueeHero from "@/ui/pages/entity/MarqueeHero";

interface ComedianDetailHeaderProps {
    comedian: ComedianDTO;
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
}) => {
    const { mv, mp, springs, prefersReducedMotion } = useMotionProps();
    const [showConfetti, setShowConfetti] = useState(false);

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

    return (
        <section className="relative w-full">
            <div className="pointer-events-none absolute inset-x-0 top-0 z-20 mx-auto max-w-7xl">
                {/* Favorite button — pinned to top-right of the hero */}
                <motion.div
                    whileHover={mp({
                        scale: 1.1,
                        transition: springs.tapFeedback,
                    })}
                    whileTap={mp({
                        scale: MOTION_TAP_SCALE,
                        transition: springs.tapFeedback,
                    })}
                    className="pointer-events-auto absolute top-4 right-4 sm:top-6 sm:right-6"
                >
                    <button
                        onClick={handleFavoriteWithAnimation}
                        aria-label={
                            isFavorite
                                ? "Remove from favorites"
                                : "Add to favorites"
                        }
                        aria-pressed={isFavorite}
                        className="p-2.5 bg-surface/95 backdrop-blur-sm rounded-full shadow-card ring-1 ring-subtle hover:bg-surface-elevated hover:shadow-floating transition"
                    >
                        <Heart
                            aria-hidden="true"
                            className={`w-5 h-5 ${
                                isFavorite
                                    ? "text-accent-strong fill-current"
                                    : "text-muted-foreground"
                            }`}
                        />
                    </button>
                </motion.div>
            </div>

            <MarqueeHero
                title={parsedComedian.name}
                imageSrc={comedian.imageUrl}
                imageAlt={parsedComedian.name}
                fallback={
                    <ComedianAvatarFallback
                        name={parsedComedian.name}
                        variant="hero"
                    />
                }
            >
                <div className="flex max-w-3xl flex-col items-center">
                    {upcomingShowsLabel && (
                        <motion.p
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{
                                ...springs.contentEntrance,
                                delay: mv(0.1),
                            }}
                            className="text-lead font-dmSans text-white/75 drop-shadow"
                        >
                            {upcomingShowsLabel}
                        </motion.p>
                    )}

                    {!hasUpcomingShows && (
                        <motion.div
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{
                                ...springs.contentEntrance,
                                delay: mv(0.15),
                            }}
                            className="mt-5 flex justify-center md:justify-start lg:justify-start"
                        >
                            <Button
                                type="button"
                                variant="roundedShimmer"
                                onClick={handleNotifyClick}
                                disabled={isFavorite}
                                aria-pressed={isFavorite}
                                className="min-h-12 gap-2 rounded-full border border-white/10 px-7 py-3 text-base shadow-floating"
                            >
                                <Bell className="h-5 w-5" aria-hidden="true" />
                                {isFavorite
                                    ? "Notifications on"
                                    : "Notify me about shows"}
                            </Button>
                        </motion.div>
                    )}

                    {/* Social row */}
                    {socialLinks.length > 0 && (
                        <motion.ul
                            initial={{ opacity: 0, y: mv(10) }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{
                                ...springs.contentEntrance,
                                delay: mv(0.2),
                            }}
                            className="mt-5 flex flex-wrap justify-center gap-2"
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
                                            className="inline-flex items-center gap-2 rounded-full bg-surface/95 hover:bg-surface-elevated text-foreground px-3 py-1.5 text-caption font-dmSans font-semibold shadow-card ring-1 ring-subtle transition-colors"
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
            </MarqueeHero>

            {/* Confetti burst */}
            <AnimatePresence>
                {showConfetti && (
                    <motion.div
                        initial={{ opacity: mv(0, 1), scale: mv(0, 1) }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: mv(0, 1), scale: mv(0, 1) }}
                        transition={
                            prefersReducedMotion ? { duration: 0 } : undefined
                        }
                        className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center"
                    >
                        <Sparkles
                            aria-hidden="true"
                            className="w-12 h-12 text-yellow-400"
                        />
                    </motion.div>
                )}
            </AnimatePresence>
        </section>
    );
};

export default ComedianDetailHeader;
