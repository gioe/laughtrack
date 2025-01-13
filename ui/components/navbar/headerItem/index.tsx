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
            className={`transition-colors font-dmSans ${
                highlighted
                    ? `${styleConfig.headerItemColorHighlighted}`
                    : `${styleConfig.baseHeaderItemColor} hover:${styleConfig.baseHeaderItemHoverColor}`
            }`}
        >
            {title}
        </a>
    );
}
