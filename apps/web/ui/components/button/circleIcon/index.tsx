"use client";

import { useStyleContext } from "@/contexts/StyleProvider";
import { ReactNode } from "react";
import { Loader2 } from "lucide-react";

interface CircleIconButtonProps {
    // Essential props
    children: ReactNode;

    // Event handlers
    handleClick?: () => void;

    // Button states
    isLoading?: boolean;
    isDisabled?: boolean;

    // Button attributes
    type?: "submit" | "reset" | "button";
    ariaLabel?: string;
    title?: string;

    // Styling
    size?: "sm" | "md" | "lg";
    className?: string;
}

const sizeClasses = {
    sm: "p-2",
    md: "p-4",
    lg: "p-6",
};

export function CircleIconButton({
    children,
    handleClick,
    isLoading = false,
    isDisabled = false,
    type = "button",
    ariaLabel,
    title,
    size = "md",
    className = "",
}: CircleIconButtonProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();

    // Combine base styles with size and custom classes
    const buttonClasses = `
        ${sizeClasses[size]}
        ${styleConfig.iconBgColor}
        rounded-full
        flex
        mx-2
        items-center
        justify-center
        transition-all
        duration-200
        relative
        ${isLoading || isDisabled ? "opacity-70 cursor-not-allowed" : "hover:scale-105 active:scale-95"}
        focus:outline-none
        focus:ring-2
        focus:ring-offset-2
        focus:ring-current
        ${className}
    `.trim();

    return (
        <button
            type={type}
            disabled={isLoading || isDisabled}
            onClick={handleClick}
            className={buttonClasses}
            aria-label={ariaLabel}
            title={title}
            aria-busy={isLoading}
        >
            {/* Loading Spinner */}
            {isLoading ? (
                <span className="absolute inset-0 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin" />
                </span>
            ) : null}

            {/* Button Content */}
            <span className={isLoading ? "opacity-0" : "opacity-100"}>
                {children}
            </span>
        </button>
    );
}
