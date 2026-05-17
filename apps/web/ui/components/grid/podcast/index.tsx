"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks/useMotionProps";
import PodcastSearchCard from "@/ui/components/cards/podcast";
import type { PodcastDTO } from "@/lib/data/podcast/interface";

interface PodcastGridProps {
    podcasts: PodcastDTO[];
}

const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.05 } },
};

const cardVariants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0 },
};

export default function PodcastGrid({ podcasts }: PodcastGridProps) {
    const { prefersReducedMotion } = useMotionProps();
    const [hasAnimated, setHasAnimated] = useState(false);

    useEffect(() => {
        setHasAnimated(true);
    }, []);

    const shouldAnimate = !prefersReducedMotion;

    if (podcasts.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center px-4 py-12">
                <h2 className="mb-4 text-center font-dmSans text-hero font-bold text-foreground">
                    No results found
                </h2>
                <p className="text-center font-dmSans text-lg text-gray-600">
                    Try another podcast or host name.
                </p>
            </div>
        );
    }

    return (
        <motion.div
            className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
            variants={shouldAnimate ? containerVariants : undefined}
            initial={shouldAnimate && !hasAnimated ? "hidden" : false}
            animate={shouldAnimate ? "visible" : undefined}
        >
            {podcasts.map((podcast) => (
                <motion.div
                    key={podcast.id}
                    variants={shouldAnimate ? cardVariants : undefined}
                >
                    <PodcastSearchCard podcast={podcast} />
                </motion.div>
            ))}
        </motion.div>
    );
}
