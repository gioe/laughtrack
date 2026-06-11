import type { ReactNode } from "react";

interface SearchBarLayoutProps {
    children: ReactNode;
    maxWidth?: string;
}

interface SearchChipRowProps {
    children: ReactNode;
    ariaLabel: string;
}

// Horizontal pill-chip row rendered under the search field — the web analogue
// of iOS's chip row (LaughTrackChipPicker / ChipFlowLayout). Wraps at narrow
// widths so chips reflow instead of truncating.
export function SearchChipRow({ children, ariaLabel }: SearchChipRowProps) {
    return (
        <div
            className="flex flex-wrap items-center gap-2"
            role="group"
            aria-label={ariaLabel}
        >
            {children}
        </div>
    );
}

// Unboxed vertical stack: pill search field on top, chip row below — mirrors
// iOS's LaughTrackSearchField + chip row composition. The boxed WHERE/WHEN
// panel this replaced (border + shadow + section dividers) is intentionally
// gone; location and date controls live in the chip row instead.
export default function SearchBarLayout({
    children,
    maxWidth = "max-w-7xl",
}: SearchBarLayoutProps) {
    return (
        <div className={`w-full mx-auto ${maxWidth} flex flex-col gap-3`}>
            {children}
        </div>
    );
}
