"use client";

import Link from "next/link";
import { twMerge } from "tailwind-merge";

interface FullRoundedButtonProps {
    handleClick?: () => void;
    href?: string | null | undefined;
    label: string;
    isLoading?: boolean;
    type?: "submit" | "reset" | "button";
    color?: string;
}

export function FullRoundedButton({
    handleClick,
    label,
    isLoading,
    type = "submit",
    href = undefined,
    color = "bg-copper",
}: FullRoundedButtonProps) {
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
            className={twMerge(baseClasses, color)}
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
