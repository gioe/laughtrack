"use client";
import { FunnelIcon } from "@heroicons/react/24/outline";

interface FunnelButtonProps {
    handleClick: (open: boolean) => void;
}

export function FunnelButton({ handleClick }: FunnelButtonProps) {
    return (
        <button type="button" onClick={() => handleClick(true)}>
            <FunnelIcon className="size-7" />
        </button>
    );
}
