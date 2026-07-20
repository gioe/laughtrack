import type { ReactNode } from "react";

type Props = {
    rowName: string;
    children: ReactNode;
};

export function ComedianProfileSection({ rowName, children }: Props) {
    return (
        <div
            role="group"
            aria-label={`Name and blocklist status for ${rowName}`}
            className="grid min-w-0 gap-4 rounded-md border border-copper/15 bg-coconut-cream/35 p-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end"
        >
            {children}
        </div>
    );
}
