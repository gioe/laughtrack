"use client";

import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { ChevronDown, ChevronRight } from "lucide-react";

type Props = {
    row: AdminComedianListItem;
    open: boolean;
    disabled: boolean;
    onToggle: () => void;
    onUnblock: () => void;
};

function formatDate(iso: string | null) {
    if (!iso) return null;
    return iso.replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function currentAvatarUrl(row: AdminComedianListItem) {
    if (row.activeImageAsset) return row.activeImageAsset.avatarUrl ?? "";
    return row.hasImage ? row.nameImageUrl : "";
}

function ComedianRowHeadshot({ row }: { row: AdminComedianListItem }) {
    const src = currentAvatarUrl(row);
    if (!src) return null;
    return (
        <img
            src={src}
            alt={`${row.name} headshot`}
            className="h-11 w-11 shrink-0 rounded-md border border-copper/25 object-cover"
        />
    );
}

export function BlockedComedianRow({
    row,
    open,
    disabled,
    onToggle,
    onUnblock,
}: Props) {
    return (
        <li className="px-4 py-3">
            <button
                type="button"
                aria-expanded={open}
                aria-controls={`comedian-row-${row.id}`}
                onClick={onToggle}
                className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-red-50/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-copper/40"
            >
                {open ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-cedar" />
                ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-cedar" />
                )}
                <ComedianRowHeadshot row={row} />
                <span className="min-w-0 flex-1">
                    <span
                        role="heading"
                        aria-level={2}
                        className="block break-words font-urbanist-bold text-h3 leading-tight text-cedar"
                    >
                        {row.name}
                    </span>
                    <span className="mt-1 block font-dmSans text-caption font-semibold text-soft-charcoal">
                        ID {row.id}
                    </span>
                </span>
                <span className="shrink-0 rounded-md border border-red-700/30 bg-red-50 px-2.5 py-1 font-dmSans text-caption font-semibold text-red-900">
                    Blocked
                </span>
            </button>
            <div
                id={`comedian-row-${row.id}`}
                hidden={!open}
                className={`mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_auto] ${
                    open ? "" : "hidden"
                }`}
            >
                <div className="rounded-md border border-red-700/25 bg-red-50 p-3 font-dmSans text-body text-red-950">
                    <div className="font-semibold">
                        {row.blockReason ?? "Blocked comedian"}
                    </div>
                    <div className="mt-1 text-caption text-red-900">
                        {row.blockAddedBy ?? "Unknown admin"}
                        {row.blockAddedAt
                            ? ` · ${formatDate(row.blockAddedAt)}`
                            : ""}
                    </div>
                </div>
                <label className="inline-flex w-fit items-center gap-2 rounded-md border border-red-800/35 bg-white px-3 py-2 font-dmSans text-body font-semibold text-red-950">
                    <input
                        type="checkbox"
                        checked
                        disabled={disabled}
                        onChange={() => void onUnblock()}
                        aria-label={`Blocked status for ${row.name}`}
                        className="h-4 w-4 accent-red-800 disabled:accent-soft-charcoal"
                    />
                    Blocked
                </label>
            </div>
        </li>
    );
}
