"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
    rowId: number;
    open: boolean;
    onToggle: () => void;
    idPrefix: string;
    title: ReactNode;
    contentClassName: string;
    children: ReactNode;
};

export function ComedianEditorSection({
    rowId,
    open,
    onToggle,
    idPrefix,
    title,
    contentClassName,
    children,
}: Props) {
    const contentId = `comedian-${idPrefix}-${rowId}`;
    return (
        <div
            role="listitem"
            className="overflow-hidden rounded-md border border-copper/20 bg-white"
        >
            <button
                type="button"
                aria-expanded={open}
                aria-controls={contentId}
                onClick={onToggle}
                className="flex w-full items-center gap-2 bg-coconut-cream/45 px-3 py-3 text-left transition-colors hover:bg-coconut-cream/70"
            >
                {open ? (
                    <ChevronDown className="h-4 w-4 shrink-0 text-cedar" />
                ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 text-cedar" />
                )}
                <span className="min-w-0 font-dmSans text-caption font-semibold uppercase tracking-wide text-soft-charcoal">
                    {title}
                </span>
            </button>
            {open ? (
                <div id={contentId} className={contentClassName}>
                    {children}
                </div>
            ) : null}
        </div>
    );
}
