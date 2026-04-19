import React from "react";

interface WebIconProps {
    className?: string;
    size?: string;
}

const WebIcon = ({ className = "", size = "w-10 h-10" }: WebIconProps) => {
    return (
        <div
            className={`${size} rounded-full bg-copper-bright flex items-center justify-center ${className}`}
        >
            <svg
                viewBox="0 0 24 24"
                className="w-full h-full text-white"
                fill="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
            >
                <path d="M17.5 3h-11A4.27 4.27 0 0 0 2 7v6a4.27 4.27 0 0 0 4.5 4h11a4.27 4.27 0 0 0 4.5-4V7a4.27 4.27 0 0 0-4.5-4v0ZM12 17v4M15.9 21h-8" />
            </svg>
        </div>
    );
};

export default WebIcon;
