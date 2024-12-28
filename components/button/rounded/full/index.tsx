"use client";

interface FullRoundedButtonProps {
    handleClick?: () => void;
    label: string;
    isLoading?: boolean;
}

export function FullRoundedButton({
    handleClick,
    label,
    isLoading,
}: FullRoundedButtonProps) {
    return (
        <>
            <button
                disabled={isLoading}
                onClick={() => {
                    if (handleClick) {
                        handleClick();
                    }
                }}
                className="bg-champagne text-copper font-bold py-2 px-4 rounded-full"
            >
                {label}
            </button>
        </>
    );
}
