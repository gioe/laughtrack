import Link from "next/link";
import { cn } from "@/util/tailwindUtil";

interface SectionHeaderProps {
    eyebrow?: string;
    title: string;
    subtitle?: string;
    actionHref?: string;
    actionLabel?: string;
    titleId?: string;
    className?: string;
}

const SectionHeader = ({
    eyebrow,
    title,
    subtitle,
    actionHref,
    actionLabel,
    titleId,
    className,
}: SectionHeaderProps) => {
    const hasAction = Boolean(actionHref && actionLabel);

    return (
        <header
            className={cn(
                "flex flex-col gap-2 mb-4",
                hasAction &&
                    "sm:flex-row sm:items-baseline sm:justify-between sm:gap-4",
                className,
            )}
        >
            <div className="flex flex-col gap-1">
                {eyebrow && (
                    <span className="font-dmSans text-xs font-semibold uppercase tracking-widest text-copper">
                        {eyebrow}
                    </span>
                )}
                <h2
                    id={titleId}
                    className="font-urbanist-bold text-h2 font-bold text-foreground"
                >
                    {title}
                </h2>
                {subtitle && (
                    <p className="text-muted-foreground font-dmSans text-body">
                        {subtitle}
                    </p>
                )}
            </div>
            {hasAction && (
                <Link
                    href={actionHref!}
                    className="font-dmSans text-sm font-semibold text-copper hover:underline whitespace-nowrap"
                >
                    {actionLabel} →
                </Link>
            )}
        </header>
    );
};

export default SectionHeader;
