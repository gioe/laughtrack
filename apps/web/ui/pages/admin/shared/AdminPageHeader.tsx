type AdminPageHeaderProps = {
    eyebrow: string;
    title: string;
    description?: string;
    summary?: string;
};

export default function AdminPageHeader({
    eyebrow,
    title,
    description,
    summary,
}: AdminPageHeaderProps) {
    return (
        <div>
            <p className="font-dmSans text-caption font-semibold uppercase text-copper-dark">
                {eyebrow}
            </p>
            <h1 className="mt-1 font-chivo text-h1 text-cedar">{title}</h1>
            {description && (
                <p className="mt-2 max-w-3xl font-dmSans text-body text-soft-charcoal">
                    {description}
                </p>
            )}
            {summary && (
                <p className="mt-2 font-dmSans text-body text-soft-charcoal">
                    {summary}
                </p>
            )}
        </div>
    );
}
