import React from "react";

const XIcon = ({ className = "", size = "w-5 h-5" }) => {
    return (
        <div
            className={`${size} rounded-full bg-[#CD6837] flex items-center justify-center ${className}`}
        >
            <svg
                viewBox="0 0 24 24"
                className="w-full h-full text-white"
                fill="currentColor"
            >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.258 5.63 5.906-5.63zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
        </div>
    );
};

export default XIcon;
