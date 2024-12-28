"use client";

interface HeaderItemProps {
    href?: string;
    title: string;
}

export function HeaderItem({ href, title }: HeaderItemProps) {
    return (
        <a href={href} className="text-copper">
            {title}
        </a>
    );
}
