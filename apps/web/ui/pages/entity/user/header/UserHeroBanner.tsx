"use client";

import React, { useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";

interface UserHeroBannerProps {
    name: string | null | undefined;
    email: string | null | undefined;
    image: string | null | undefined;
}

const UserHeroBanner = ({ name, email, image }: UserHeroBannerProps) => {
    const { mv, mt, prefersReducedMotion } = useMotionProps();
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={mt({ duration: 0.4 })}
            className="relative w-full h-48 md:h-64 overflow-hidden rounded-xl"
        >
            {/* Gradient fallback background */}
            <div className="absolute inset-0 bg-gradient-to-br from-copper/60 via-cedar/40 to-stone-800" />

            {/* Hero image */}
            {image && !imageError && (
                <>
                    <Image
                        src={image}
                        alt={name || "Profile"}
                        fill
                        className={`object-cover object-center transition-opacity duration-500 ${
                            imageLoaded ? "opacity-100" : "opacity-0"
                        }`}
                        onError={() => setImageError(true)}
                        onLoad={() => setImageLoaded(true)}
                        priority
                        sizes="(max-width: 768px) 100vw, 1280px"
                    />
                    {/* Skeleton pulse during image load */}
                    {!imageLoaded && (
                        <div
                            className={`absolute inset-0 bg-stone-700${!prefersReducedMotion ? " animate-pulse" : ""}`}
                        />
                    )}
                    {/* Overlay gradient — only when image is present */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                </>
            )}

            {/* Name + email overlaid at bottom */}
            <div className="absolute bottom-0 left-0 right-0 p-6">
                <motion.h1
                    initial={{ opacity: 0, y: mv(20) }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={mt({ duration: 0.3, delay: mv(0.1) })}
                    className="text-3xl md:text-4xl font-bold text-white drop-shadow-lg font-gilroy-bold"
                >
                    {name || "Comedy Fan"}
                </motion.h1>
                <motion.p
                    initial={{ opacity: 0, y: mv(10) }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={mt({ duration: 0.3, delay: mv(0.2) })}
                    className="text-white/80"
                >
                    {email}
                </motion.p>
            </div>
        </motion.div>
    );
};

export default UserHeroBanner;
