"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Check, ChevronDown, MapPin } from "lucide-react";

export interface ChainLocation {
    name: string;
    locationLabel: string | null;
    isCurrent: boolean;
}

interface ChainLocationDropdownProps {
    chainName: string;
    locations: ChainLocation[];
}

// Compact switcher for the other venues in a club's chain. Replaces the former
// "Locations" card grid: selecting a location navigates to that club's detail
// page. Renders nothing unless the chain has more than one location.
const ChainLocationDropdown: React.FC<ChainLocationDropdownProps> = ({
    chainName,
    locations,
}) => {
    const [open, setOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const current = locations.find((location) => location.isCurrent);

    useEffect(() => {
        if (!open) return;
        const onPointerDown = (event: MouseEvent) => {
            if (
                containerRef.current &&
                !containerRef.current.contains(event.target as Node)
            ) {
                setOpen(false);
            }
        };
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") setOpen(false);
        };
        document.addEventListener("mousedown", onPointerDown);
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("mousedown", onPointerDown);
            document.removeEventListener("keydown", onKeyDown);
        };
    }, [open]);

    if (locations.length <= 1) return null;

    return (
        <div
            ref={containerRef}
            className="relative inline-block w-full max-w-sm"
        >
            <span className="mb-1 block font-dmSans text-caption font-semibold uppercase tracking-wide text-foreground/55">
                {chainName} · {locations.length} locations
            </span>
            <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-haspopup="listbox"
                aria-expanded={open}
                className="flex w-full items-center justify-between gap-3 rounded-lg border border-copper/30 bg-white/5 px-4 py-2.5 font-dmSans text-body text-foreground transition hover:border-copper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-copper"
            >
                <span className="flex min-w-0 items-center gap-2">
                    <MapPin
                        className="h-4 w-4 shrink-0 text-copper-bright"
                        aria-hidden="true"
                    />
                    <span className="truncate">
                        {current?.name ?? "Select location"}
                    </span>
                </span>
                <ChevronDown
                    className={`h-4 w-4 shrink-0 text-copper-bright transition-transform ${
                        open ? "rotate-180" : ""
                    }`}
                    aria-hidden="true"
                />
            </button>
            {open && (
                <ul
                    role="listbox"
                    aria-label={`${chainName} locations`}
                    className="absolute left-0 right-0 z-20 mt-2 max-h-80 overflow-auto rounded-lg border border-copper/20 bg-[#1c1c1c] py-1 shadow-xl"
                >
                    {locations.map((location) => {
                        const body = (
                            <>
                                <span className="flex min-w-0 flex-col">
                                    <span className="truncate font-semibold text-foreground">
                                        {location.name}
                                    </span>
                                    {location.locationLabel && (
                                        <span className="truncate text-caption text-foreground/55">
                                            {location.locationLabel}
                                        </span>
                                    )}
                                </span>
                                {location.isCurrent && (
                                    <Check
                                        className="h-4 w-4 shrink-0 text-copper-bright"
                                        aria-hidden="true"
                                    />
                                )}
                            </>
                        );

                        if (location.isCurrent) {
                            return (
                                <li
                                    key={location.name}
                                    role="option"
                                    aria-selected="true"
                                    aria-current="true"
                                    className="flex items-center justify-between gap-3 bg-copper/10 px-4 py-2.5 font-dmSans"
                                >
                                    {body}
                                </li>
                            );
                        }

                        return (
                            <li
                                key={location.name}
                                role="option"
                                aria-selected="false"
                            >
                                <Link
                                    href={`/club/${location.name}`}
                                    onClick={() => setOpen(false)}
                                    className="flex items-center justify-between gap-3 px-4 py-2.5 font-dmSans transition hover:bg-white/5 focus-visible:bg-white/5 focus-visible:outline-none"
                                >
                                    {body}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
};

export default ChainLocationDropdown;
