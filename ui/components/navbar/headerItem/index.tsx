"use client";

import { useStyleContext } from "@/contexts/StyleProvider";

interface HeaderItemProps {
    href?: string;
    title: string;
    highlighted: boolean;
}

export function HeaderItem({ href, title, highlighted }: HeaderItemProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    return (
        <a
            href={href}
            className={`
                font-semibold 
                font-dmSans 
                transition-opacity 
                duration-200 
                ${styleConfig.baseHeaderItemColor}
                ${highlighted ? "opacity-100" : "opacity-50 hover:opacity-75"}
            `}
        >
            {title}
        </a>
    );
}
