"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import Link from "next/link";
import { twMerge } from "tailwind-merge";

interface FullRoundedButtonProps {
    handleClick?: () => void;
    href?: string | null | undefined;
    label: string;
    isLoading?: boolean;
    type?: "submit" | "reset" | "button";
}

export function FullRoundedButton({
    handleClick,
    label,
    isLoading,
    type = "submit",
    href = undefined,
}: FullRoundedButtonProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const baseClasses =
        "px-6 py-2 text-white rounded-lg transition-colors duration-200 font-medium font-dmSans";

    const ButtonComponent = () => (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className={twMerge(baseClasses, styleConfig.buttonBgColor)}
        >
            {label}
        </button>
    );

    if (!href) {
        return <ButtonComponent />;
    }

    return (
        <Link href={href}>
            <ButtonComponent />
        </Link>
    );
}
