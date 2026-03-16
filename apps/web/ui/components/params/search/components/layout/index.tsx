import type { ReactNode } from "react";
import SearchBarContainer from "../container";

interface SearchBarLayoutProps {
    children: ReactNode;
    maxWidth?: string;
}

interface SearchBarSectionProps {
    children: ReactNode;
    first?: boolean;
    last?: boolean;
}

export function SearchBarSection({
    children,
    first,
    last,
}: SearchBarSectionProps) {
    const both = first && last;
    const padding = both
        ? ""
        : first
          ? "lg:pr-6"
          : last
            ? "lg:pl-6"
            : "lg:pl-6 lg:pr-6";
    const margin = last ? "" : "mb-6 lg:mb-0";
    return (
        <div
            className={["w-full lg:w-auto", margin, padding]
                .filter(Boolean)
                .join(" ")}
        >
            {children}
        </div>
    );
}

export default function SearchBarLayout({
    children,
    maxWidth = "max-w-7xl",
}: SearchBarLayoutProps) {
    return (
        <SearchBarContainer maxWidth={maxWidth}>
            <div className="flex flex-col lg:flex-row items-center lg:divide-x divide-white/10">
                {children}
            </div>
        </SearchBarContainer>
    );
}
