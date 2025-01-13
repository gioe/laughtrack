"use client";
import { Bars3Icon } from "@heroicons/react/20/solid";

interface FunnelButtonProps {
    handleClick: (open: boolean) => void;
}

export function HamburgerMenuButton({ handleClick }: FunnelButtonProps) {
    return (
        <button
            type="button"
            onClick={() => handleClick(true)}
            className="text-gray-400 hover:text-gray-500"
        >
            <span className="sr-only">Open main menu</span>
            <Bars3Icon aria-hidden="true" className="h-5 w-5" />
        </button>
    );
}
