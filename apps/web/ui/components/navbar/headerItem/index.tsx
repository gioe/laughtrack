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
    const baseClasses = `text-[16px] font-semibold font-dmSans relative
        transition-all duration-300 ease-out
        after:content-[''] after:absolute after:bottom-[-4px] after:left-0
        after:w-full after:h-[2px] after:bg-copper after:transform
        after:scale-x-0 after:origin-bottom-right after:transition-transform after:duration-300 after:ease-out
        ${
            highlighted
                ? "opacity-100 after:scale-x-100 after:origin-bottom-left"
                : "opacity-70 hover:opacity-100"
        }
        hover:after:scale-x-100 hover:after:origin-bottom-left`;

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
