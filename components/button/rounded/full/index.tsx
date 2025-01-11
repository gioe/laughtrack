"use client";

interface FullRoundedButtonProps {
    handleClick?: () => void;
    label: string;
    isLoading?: boolean;
    type?: "submit" | "reset" | "button";
}

export function FullRoundedButton({
    handleClick,
    label,
    isLoading,
    type = "submit",
}: FullRoundedButtonProps) {
    return (
        <button
            type={type}
            disabled={isLoading}
            onClick={() => {
                if (handleClick) {
                    handleClick();
                }
            }}
            className="px-6 py-2 text-white bg-copper rounded-full transition-colors duration-200 font-medium font-dmSans"
        >
            {label}
        </button>
    );
}
