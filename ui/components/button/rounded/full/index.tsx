"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { styleContexts } from "@/ui/components/header/styles";
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
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    const ButtonComponent = () => (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className={`px-6 py-2 text-white ${styleConfig?.buttonColor} rounded-lg transition-colors duration-200 font-medium font-dmSans`}
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
