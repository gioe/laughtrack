"use client";

interface HeaderItemProps {
    href?: string;
    title: string;
    highlighted: boolean;
}

export function HeaderItem({ href, title, highlighted }: HeaderItemProps) {
    return (
        <a
            href={href}
            className={`transition-colors font-dmSans ${
                highlighted ? "text-white" : "text-gray-400 hover:text-white"
            }`}
        >
            {title}
        </a>
    );
}
