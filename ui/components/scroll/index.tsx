"use client";

import React from "react";
import NavButton from "./button";

interface ScrollButtonsProps {
    leftOnClick: () => void;
    rightOnClick: () => void;
    leftDisabled?: boolean;
    rightDisabled?: boolean;
    className?: string;
    size?: "small" | "medium" | "large";
    ariaLabels?: {
        leftButton?: string;
        rightButton?: string;
    };
}

/**
 * ScrollButtons component for horizontal navigation
 *
 * @param leftOnClick - Function to call when left button is clicked
 * @param rightOnClick - Function to call when right button is clicked
 * @param leftDisabled - Whether the left button should be disabled
 * @param rightDisabled - Whether the right button should be disabled
 * @param className - Additional classes for the button container
 * @param size - Size variant for the buttons
 * @param ariaLabels - Accessibility labels for the buttons
 */
const ScrollButtons = ({
    leftOnClick,
    rightOnClick,
    leftDisabled = false,
    rightDisabled = false,
    className = "",
    size = "medium",
    ariaLabels = {
        leftButton: "Scroll left",
        rightButton: "Scroll right",
    },
}: ScrollButtonsProps) => {
    return (
        <div
            className={`flex gap-2 ${className}`}
            role="group"
            aria-label="Scroll controls"
        >
            <NavButton
                direction="left"
                onClick={leftOnClick}
                disabled={leftDisabled}
                size={size}
                ariaLabel={ariaLabels.leftButton}
            />
            <NavButton
                direction="right"
                onClick={rightOnClick}
                disabled={rightDisabled}
                size={size}
                ariaLabel={ariaLabels.rightButton}
            />
        </div>
    );
};

export default ScrollButtons;
