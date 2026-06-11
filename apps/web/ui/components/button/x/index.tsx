"use client";
import { XMarkIcon } from "@heroicons/react/20/solid";

interface FunnelButtonProps {
    handleClick: (open: boolean) => void;
}

export function XButton({ handleClick }: FunnelButtonProps) {
    return (
        <button
            type="button"
            onClick={() => handleClick(true)}
            className="text-muted-foreground hover:text-foreground"
        >
            <span className="sr-only">Close</span>
            <XMarkIcon aria-hidden="true" className="h-6 w-6" />
        </button>
    );
}
