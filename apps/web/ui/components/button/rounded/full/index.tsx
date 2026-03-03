"use client";

import Link from "next/link";
import { twMerge } from "tailwind-merge";

interface FullRoundedButtonProps {
    handleClick?: () => void;
    href?: string | null | undefined;
    label: string;
    disabled?: boolean;
    type?: "submit" | "reset" | "button";
    color?: string;
}

export function FullRoundedButton({
    handleClick,
    label,
    disabled,
    type = "submit",
    href = undefined,
    color = "bg-copper",
}: FullRoundedButtonProps) {
    const baseClasses = `
        px-6 py-2.5 text-white rounded-lg font-bold text-[16px] font-dmSans
        transform transition-all duration-200 ease-in-out
        shadow-sm hover:shadow-md
        hover:-translate-y-[1px] hover:scale-[1.02]
        active:translate-y-[1px] active:scale-[0.98]
        disabled:opacity-50 disabled:cursor-not-allowed
        disabled:hover:translate-y-0 disabled:hover:scale-100
        relative overflow-hidden
        before:absolute before:inset-0 before:bg-white/20
        before:translate-x-[-100%] before:hover:translate-x-[100%]
        before:transition-transform before:duration-500
    `;

    const ButtonComponent = () => (
        <button
            type={type}
            disabled={disabled}
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
