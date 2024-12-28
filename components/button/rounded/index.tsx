"use client";

interface RoundedButtonProps {
    handleClick: () => void;
    title: string;
}

export function RoundedButton({ handleClick, title }: RoundedButtonProps) {
    return (
        <>
            <button
                onClick={() => {
                    handleClick();
                }}
                className="bg-champagne hover:bg-champagne text-copper font-bold py-2 px-4 rounded-full"
            >
                {title}
            </button>
        </>
    );
}
