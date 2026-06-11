import React from "react";

/**
 * Paper-ticket card with a perforated tear line, mirroring the iOS
 * ShowDetailView ticket stub (TicketShape / TicketTheme). The cream surface is
 * intentional — this is the one light surface on the dark canvas, matching the
 * iOS treatment.
 *
 * Body rows render above the perforation; the `stub` slot renders below it as
 * the tear-off section. The edge notches are canvas-colored half circles
 * clipped by the card's rounded overflow, which reads as semicircular cutouts
 * against the uniform page background.
 */

interface TicketStubProps {
    /** Rows above the perforation (typically TicketStubRow elements). */
    children: React.ReactNode;
    /** Tear-off section below the perforation. */
    stub: React.ReactNode;
    className?: string;
}

export const TicketStub: React.FC<TicketStubProps> = ({
    children,
    stub,
    className,
}) => (
    <div
        className={`relative overflow-hidden rounded-2xl border border-copper-dark/40 bg-champagne ${className ?? ""}`}
    >
        <div className="divide-y divide-copper-dark/20 px-4">{children}</div>
        <TicketPerforation />
        <div className="px-4">{stub}</div>
    </div>
);

// Dashed tear line flanked by two notches. The notch circles are filled with
// the page canvas color (coconut-cream) and centered on the card edges, so the
// card's overflow-hidden clipping leaves only the inner half visible — a
// concave cutout with its own border arc.
const TicketPerforation: React.FC = () => (
    <div className="relative h-5" aria-hidden="true">
        <span className="absolute left-0 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-copper-dark/40 bg-coconut-cream" />
        <span className="absolute right-0 top-1/2 h-5 w-5 -translate-y-1/2 translate-x-1/2 rounded-full border border-copper-dark/40 bg-coconut-cream" />
        <div className="absolute left-5 right-5 top-1/2 border-t border-dashed border-copper-dark/40" />
    </div>
);

interface TicketStubRowProps {
    /** Leading icon, rendered inside a paper-shade circle in copper ink. */
    icon: React.ReactNode;
    /** Uppercase eyebrow label (WHEN / VENUE / TICKETS). */
    label: string;
    value: React.ReactNode;
    /** Optional trailing affordance (e.g. the BUY TICKETS pill). */
    trailing?: React.ReactNode;
}

export const TicketStubRow: React.FC<TicketStubRowProps> = ({
    icon,
    label,
    value,
    trailing,
}) => (
    <div className="flex items-center gap-3.5 py-3">
        <span
            aria-hidden="true"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-copper-dark/10 text-copper-dark"
        >
            {icon}
        </span>
        <div className="min-w-0 flex-1">
            <p className="font-dmSans text-caption font-bold uppercase tracking-wider text-copper-dark">
                {label}
            </p>
            <div className="font-dmSans text-sm font-semibold text-coconut-cream sm:text-base">
                {value}
            </div>
        </div>
        {trailing}
    </div>
);
