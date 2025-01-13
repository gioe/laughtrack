"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { Search } from "lucide-react";
import { ReactNode } from "react";

interface CircleIconButtonProps {
    handleClick?: () => void;
    isLoading?: boolean;
    type?: "submit" | "reset" | "button";
    children: ReactNode;
}

export function CircleIconButton({
    handleClick,
    isLoading,
    type = "submit",
    children,
}: CircleIconButtonProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    return (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className={`p-4 ${styleConfig.iconBgColor} hover:${styleConfig.iconBgColor} rounded-full flex items-center justify-center transition-colors mx-2`}
        >
            {children}
        </button>
    );
}
