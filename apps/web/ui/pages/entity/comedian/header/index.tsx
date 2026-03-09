"use client";

import React, { useState } from "react";
import { Heart, Sparkles } from "lucide-react";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import SocialMediaColumn from "../social";
import { useFavorite } from "@/hooks/useFavorite";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import Image from "next/image";

const PLACEHOLDER = "/placeholders/comedian-placeholder.svg";

interface ClubDetailHeaderProps {
    comedian: ComedianDTO;
}

const ComedianDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    comedian,
}) => {
    const prefersReducedMotion = useReducedMotion();
    const [error, setError] = useState(false);
    const [showConfetti, setShowConfetti] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);

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

    return (
        <div className="max-w-7xl mx-auto p-6">
            <div className="flex flex-col md:flex-row gap-8">
                {/* Left Column - Comedian Info */}
                <div className="flex-1">
                    <div className="flex items-start gap-6">
                        <motion.div
                            initial={{
                                opacity: 0,
                                scale: prefersReducedMotion ? 1 : 0.9,
                            }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{
                                duration: prefersReducedMotion ? 0 : 0.3,
                            }}
                            className="relative"
                        >
                            <div className="relative w-24 h-24 rounded-full overflow-hidden">
                                <Image
                                    src={
                                        error ? PLACEHOLDER : comedian.imageUrl
                                    }
                                    alt={comedian.name}
                                    fill
                                    className={`object-cover transition-opacity duration-300 ${
                                        imageLoaded
                                            ? "opacity-100"
                                            : "opacity-0"
                                    }`}
                                    onError={() => setError(true)}
                                    onLoad={() => setImageLoaded(true)}
                                />
                                {!imageLoaded && (
                                    <div className="absolute inset-0 bg-gray-200 animate-pulse" />
                                )}
                            </div>
                            <motion.div
                                className="absolute -bottom-2 -right-2"
                                whileHover={
                                    prefersReducedMotion
                                        ? undefined
                                        : { scale: 1.1 }
                                }
                                whileTap={
                                    prefersReducedMotion
                                        ? undefined
                                        : { scale: 0.9 }
                                }
                            >
                                <button
                                    onClick={handleFavoriteWithAnimation}
                                    className="p-2 bg-white rounded-full shadow-lg hover:shadow-xl transition-shadow"
                                >
                                    <Heart
                                        className={`w-5 h-5 ${
                                            isFavorite
                                                ? "text-red-500 fill-current"
                                                : "text-gray-400"
                                        }`}
                                    />
                                </button>
                            </motion.div>
                        </motion.div>

                        <div className="flex-1">
                            <motion.h1
                                initial={{
                                    opacity: 0,
                                    y: prefersReducedMotion ? 0 : 20,
                                }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{
                                    duration: prefersReducedMotion ? 0 : 0.3,
                                    delay: prefersReducedMotion ? 0 : 0.1,
                                }}
                                className="text-3xl font-bold text-gray-900 mb-2"
                            >
                                {parsedComedian.name}
                            </motion.h1>
                        </div>
                    </div>
                </div>

                {/* Right Column - Social Media */}
                <div className="md:w-64">
                    <SocialMediaColumn comedian={comedian} />
                </div>
            </div>

            <AnimatePresence>
                {showConfetti && (
                    <motion.div
                        initial={{
                            opacity: prefersReducedMotion ? 1 : 0,
                            scale: prefersReducedMotion ? 1 : 0,
                        }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{
                            opacity: prefersReducedMotion ? 1 : 0,
                            scale: prefersReducedMotion ? 1 : 0,
                        }}
                        transition={{
                            duration: prefersReducedMotion ? 0 : undefined,
                        }}
                        className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                    >
                        <Sparkles className="w-12 h-12 text-yellow-400" />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default ComedianDetailHeader;
