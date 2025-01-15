"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";

interface HeaderItemProps {
    href?: string;
    title: string;
    highlighted: boolean;
}

export function HeaderItem({ href, title, highlighted }: HeaderItemProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const baseClasses = `text-xl font-semibold font-dmSans ${highlighted ? "opacity-100" : "opacity-50 hover:opacity-75"}`;

    return (
        <a
            href={href}
            className={twMerge(baseClasses, styleConfig.baseHeaderItemColor)}
        >
            {title}
        </a>
    );
}
