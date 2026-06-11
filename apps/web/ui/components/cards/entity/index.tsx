"use client";

import React from "react";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { cn } from "@/util/tailwindUtil";

export type EntityCardChrome = "warm" | "coconut-hover" | "stage" | "none";

const CHROME_CLASSES: Record<EntityCardChrome, string> = {
    // "warm": standard elevated dark card — mirrors iOS LaughTrackCard
    // standard tone (surface-elevated bg, subtle border, card shadow).
    warm: "rounded-card shadow-card border border-subtle bg-surface-elevated",
    // "coconut-hover": muted card that lifts to a copper hairline on hover.
    "coconut-hover":
        "rounded-card overflow-hidden shadow-card border border-subtle bg-surface-muted transition-all duration-300 hover:shadow-floating hover:border-copper/60",
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
