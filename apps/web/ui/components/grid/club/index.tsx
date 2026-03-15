"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubSearchCard from "../../cards/club/search";
import { useMotionProps } from "@/hooks/useMotionProps";

interface ClubGridProps {
    clubs: ClubDTO[];
}

const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.05 } },
};

const cardVariants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0 },
};

const ClubGrid = ({ clubs }: ClubGridProps) => {
    const { prefersReducedMotion } = useMotionProps();
    const [hasAnimated, setHasAnimated] = useState(false);

    useEffect(() => {
        setHasAnimated(true);
    }, []);

    const shouldAnimate = !prefersReducedMotion;

    return (
        <div className="w-full">
            {clubs.length > 0 ? (
                <motion.div
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
                    variants={shouldAnimate ? containerVariants : undefined}
                    initial={shouldAnimate && !hasAnimated ? "hidden" : false}
                    animate={shouldAnimate ? "visible" : undefined}
                >
                    {clubs.map((dto) => (
                        <motion.div
                            key={dto.name}
                            variants={shouldAnimate ? cardVariants : undefined}
                        >
                            <ClubSearchCard club={dto} />
                        </motion.div>
                    ))}
                </motion.div>
            ) : (
                <div className="flex flex-col items-center justify-center py-12 px-4">
                    <h2 className="font-bold font-dmSans text-[48px] text-center text-cedar mb-4">
                        No results found
                    </h2>
                    <p className="text-gray-600 text-center text-lg font-dmSans">
                        Does that place even exist?
                    </p>
                </div>
            )}
        </div>
    );
};

export default ClubGrid;
