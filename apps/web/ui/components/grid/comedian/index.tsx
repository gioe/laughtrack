"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianGridCard from "../../cards/comedian";
import { useMotionProps } from "@/hooks/useMotionProps";

interface ComedianGridProps {
    comedians: ComedianDTO[];
    className: string;
    isTrending?: boolean;
}

const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.05 } },
};

const cardVariants = {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0 },
};

const ComedianGrid = ({
    comedians,
    className,
    isTrending,
}: ComedianGridProps) => {
    const { prefersReducedMotion } = useMotionProps();
    const [hasAnimated, setHasAnimated] = useState(false);

    useEffect(() => {
        setHasAnimated(true);
    }, []);

    const shouldAnimate = !prefersReducedMotion;

    return (
        <div className="w-full">
            {comedians.length > 0 ? (
                <motion.div
                    className={className}
                    variants={shouldAnimate ? containerVariants : undefined}
                    initial={shouldAnimate && !hasAnimated ? "hidden" : false}
                    animate={shouldAnimate ? "visible" : undefined}
                >
                    {comedians.map((dto) => (
                        <motion.div
                            key={dto.name}
                            variants={shouldAnimate ? cardVariants : undefined}
                        >
                            <ComedianGridCard
                                entity={dto}
                                isTrending={isTrending}
                            />
                        </motion.div>
                    ))}
                </motion.div>
            ) : (
                <div className="flex flex-col items-center justify-center py-12 px-4">
                    <h3 className="font-bold font-dmSans text-[48px] text-center text-cedar mb-4">
                        No results found
                    </h3>
                    <p className="text-gray-600 text-center text-lg font-dmSans">
                        That person must not be funny enough.
                    </p>
                </div>
            )}
        </div>
    );
};

export default ComedianGrid;
