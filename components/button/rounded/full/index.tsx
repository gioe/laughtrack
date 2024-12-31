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
            className="bg-champagne text-copper font-bold py-2 px-4 rounded-full hover:bg-pine-tree"
        >
            {label}
        </button>
    );
}
