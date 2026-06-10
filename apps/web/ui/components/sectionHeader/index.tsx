import Link from "next/link";

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
            className={
                "flex flex-col gap-2 mb-4" +
                (hasAction
                    ? " sm:flex-row sm:items-baseline sm:justify-between sm:gap-4"
                    : "") +
                (className ? ` ${className}` : "")
            }
        >
            <div className="flex flex-col gap-1">
                {eyebrow && (
                    <span className="font-dmSans text-xs font-semibold uppercase tracking-widest text-copper">
                        {eyebrow}
                    </span>
                )}
                <h2
                    id={titleId}
                    className="font-gilroy-bold text-h2 font-bold text-foreground"
                >
                    {title}
                </h2>
                {subtitle && (
                    <p className="text-gray-600 font-dmSans text-body">
                        {subtitle}
                    </p>
                )}
            </div>
            {hasAction && (
                <Link
                    href={actionHref!}
                    className="text-sm font-dmSans text-copper hover:underline whitespace-nowrap"
                >
                    {actionLabel} →
                </Link>
            )}
        </header>
    );
};

export default SectionHeader;
