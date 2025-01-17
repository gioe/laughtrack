"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";

export default function Logo() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const baseClasses = `text-[30px] font-bold font-chivo`;

    return (
        <div className="flex items-center">
            <span className={twMerge(baseClasses, styleConfig.logoTextColor)}>
                Laughtrack
            </span>
        </div>
    );
}
