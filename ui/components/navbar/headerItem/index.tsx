"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";

interface HeaderItemProps {
    href?: string;
    title: string;
    highlighted: boolean;
    textColor?: string;
}

export function HeaderItem({
    href,
    title,
    textColor,
    highlighted,
}: HeaderItemProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const baseClasses = `text-[16px] font-semibold font-dmSans ${highlighted ? "opacity-100" : "opacity-50 hover:opacity-75"}`;

    return (
        <a
            href={href}
            className={twMerge(
                baseClasses,
                textColor ?? styleConfig.baseHeaderItemColor,
            )}
        >
            {title}
        </a>
    );
}
