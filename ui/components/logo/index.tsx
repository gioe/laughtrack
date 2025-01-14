"use client";

import { useStyleContext } from "@/contexts/StyleProvider";

export default function Logo() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    return (
        <div className="flex items-center">
            <span
                className={`${styleConfig.logoTextColor} text-2xl font-bold font-chivo`}
            >
                Laughtrack
            </span>
        </div>
    );
}
