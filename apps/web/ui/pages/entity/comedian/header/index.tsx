"use client";

import React, { useEffect, useRef, useState } from "react";
import { Heart, Sparkles } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../social";
import { useFavorite } from "@/hooks/useFavorite";
import { motion, AnimatePresence } from "framer-motion";
import { useMotionProps } from "@/hooks";
import Image from "next/image";

const PLACEHOLDER = "/placeholders/comedian-placeholder.svg";

interface ClubDetailHeaderProps {
    comedian: ComedianDTO;
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
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

    const showImage =
        !error && !!comedian.imageUrl && comedian.imageUrl !== PLACEHOLDER;

    return (
        <div className="max-w-7xl mx-auto">
            {/* Hero Image Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={mt({ duration: 0.4 })}
                className="relative w-full h-60 sm:h-72 md:h-96 lg:h-96 xl:h-[28rem] overflow-hidden rounded-xl"
            >
                {/* Gradient fallback background */}
                <div className="absolute inset-0 bg-gradient-to-br from-slate-600 via-slate-800 to-slate-900" />

                {/* Hero image */}
                {showImage && (
                    <>
                        <Image
                            ref={imageRef}
                            src={comedian.imageUrl}
                            alt={parsedComedian.name}
                            fill
                            className={`object-cover object-top transition-opacity duration-500 ${
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
                                className={`absolute inset-0 bg-slate-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                            />
                        )}
                        {/* Overlay gradient — only when image is present */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                    </>
                )}

                {/* Name + Favorite button overlaid at bottom */}
                <div className="absolute bottom-0 left-0 right-0 p-6 flex items-end justify-between">
                    <motion.h1
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={mt({ duration: 0.3, delay: mv(0.1) })}
                        className="text-3xl md:text-4xl font-bold text-white drop-shadow-lg"
                    >
                        {parsedComedian.name}
                    </motion.h1>

                    <motion.div
                        whileHover={mp({ scale: 1.1 })}
                        whileTap={mp({ scale: 0.9 })}
                    >
                        <button
                            onClick={handleFavoriteWithAnimation}
                            aria-label={
                                isFavorite
                                    ? "Remove from favorites"
                                    : "Add to favorites"
                            }
                            aria-pressed={isFavorite}
                            className="p-3 bg-white/90 backdrop-blur-sm rounded-full shadow-lg hover:shadow-xl transition-shadow"
                        >
                            <Heart
                                aria-hidden="true"
                                className={`w-6 h-6 ${
                                    isFavorite
                                        ? "text-red-500 fill-current"
                                        : "text-gray-600"
                                }`}
                            />
                        </button>
                    </motion.div>
                </div>

                {/* Confetti burst — centered in hero */}
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

            {/* Social Links */}
            <div className="p-6">
                <SocialMediaColumn comedian={comedian} />
            </div>
        </div>
    );
};

export default ComedianDetailHeader;
