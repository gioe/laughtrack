"use client";

import React from "react";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid";

interface NavButtonProps {
    direction: "left" | "right";
    onClick: () => void;
    disabled?: boolean;
    size?: "small" | "medium" | "large";
    ariaLabel?: string;
    className?: string;
}

const NavButton = ({
    direction,
    onClick,
    disabled = false,
    size = "medium",
    ariaLabel,
    className = "",
}: NavButtonProps) => {
    // Size variants
    const sizeClasses = {
        small: "p-1.5",
        medium: "p-2",
        large: "p-3",
    };

    // Icon size
    const iconSize = {
        small: "w-4 h-4",
        medium: "w-5 h-5",
        large: "w-6 h-6",
    };

    // Button states
    const baseClasses =
        "rounded-full flex items-center justify-center transition-all duration-200";
    const activeClasses =
        "bg-cedar text-white hover:bg-cedar/90 focus:ring-2 focus:ring-cedar/50 focus:outline-none";
    const disabledClasses = "bg-gray-200 text-gray-400 cursor-not-allowed";

    // Accessibility
    const defaultAriaLabel =
        direction === "left" ? "Scroll left" : "Scroll right";

    return (
        <button
            onClick={onClick}
            disabled={disabled}
            aria-label={ariaLabel || defaultAriaLabel}
            aria-disabled={disabled}
            className={`
                ${baseClasses} 
                ${disabled ? disabledClasses : activeClasses} 
                ${sizeClasses[size]} 
                ${className}
            `}
        >
            {direction === "left" ? (
                <ChevronLeftIcon className={iconSize[size]} />
            ) : (
                <ChevronRightIcon className={iconSize[size]} />
            )}
        </button>
    );
};

export default NavButton;
