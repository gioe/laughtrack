"use client";

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
    return (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className="p-4 bg-amber-700 hover:bg-amber-800 rounded-full flex items-center justify-center transition-colors mx-2"
        >
            {children}
        </button>
    );
}
