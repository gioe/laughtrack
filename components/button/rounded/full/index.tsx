"use client";

import Link from "next/link";

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
    const ButtonComponent = () => (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className="px-6 py-2 text-white bg-copper rounded-lg transition-colors duration-200 font-medium font-dmSans"
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
