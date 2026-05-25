"use client";

import React from "react";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { cn } from "@/lib/utils";

export type EntityCardChrome = "warm" | "coconut-hover" | "stage" | "none";

const CHROME_CLASSES: Record<EntityCardChrome, string> = {
    warm: "rounded-xl shadow-md border border-white/20 bg-gradient-to-br from-white to-coconut-cream",
    "coconut-hover":
        "rounded-xl overflow-hidden shadow-sm border-b-2 border-transparent bg-gradient-to-b from-white to-coconut-cream/60 transition-all duration-300 hover:shadow-lg hover:border-copper",
    // "stage": warm near-black club-wall surface with a copper hairline. Decorative
    // brick + spotlight layers are composited inside the card by the consumer.
    stage: "rounded-xl shadow-lg shadow-black/40 border border-copper/15 bg-[#181210] transition-shadow duration-300",
    none: "",
};

interface EntityCardProps {
    as?: "div" | "article";
    chrome?: EntityCardChrome;
    className?: string;
    ariaLabel?: string;
    children: React.ReactNode;
    animateEntryY?: number;
    alreadySeen?: boolean;
    disableHover?: boolean;
}

const EntityCard: React.FC<EntityCardProps> = ({
    as = "div",
    chrome = "warm",
    className,
    ariaLabel,
    children,
    animateEntryY,
    alreadySeen,
    disableHover,
}) => {
    const { mv, mp } = useMotionProps();

    const hoverProps = disableHover
        ? {}
        : { whileHover: mp({ y: -4, transition: { duration: 0.15 } }) };

    const entryProps =
        animateEntryY != null
            ? {
                  initial: alreadySeen
                      ? (false as const)
                      : { opacity: 0, y: mv(animateEntryY) },
                  animate: { opacity: 1, y: 0 },
                  transition: { duration: mv(0.5), ease: "easeOut" as const },
              }
            : {};

    const classes = cn(CHROME_CLASSES[chrome], className);

    if (as === "article") {
        return (
            <motion.article
                aria-label={ariaLabel}
                className={classes}
                {...hoverProps}
                {...entryProps}
            >
                {children}
            </motion.article>
        );
    }
    return (
        <motion.div className={classes} {...hoverProps} {...entryProps}>
            {children}
        </motion.div>
    );
};

export default EntityCard;
