"use client";
import { FunnelIcon } from "@heroicons/react/20/solid";

interface FunnelButtonProps {
    handleClick: (open: boolean) => void;
}

export function FunnelButton({ handleClick }: FunnelButtonProps) {
    return (
        <button
            type="button"
            onClick={() => handleClick(true)}
            className="-m-2 ml-4 p-2 text-gray-400 hover:text-gray-500 sm:ml-6"
        >
            <FunnelIcon aria-hidden="true" className="h-5 w-5" />
        </button>
    );
}
