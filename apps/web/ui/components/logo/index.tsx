"use client";

import Image from "next/image";
import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";

export default function Logo() {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const baseClasses = `text-h1 font-bold font-gilroy-bold`;

    return (
        <div className="flex items-center gap-2">
            <Image
                src="/logomark.svg"
                alt="Laughtrack"
                width={28}
                height={28}
                className="shrink-0"
            />
            <span className={twMerge(baseClasses, styleConfig.logoTextColor)}>
                Laughtrack
            </span>
        </div>
    );
}
