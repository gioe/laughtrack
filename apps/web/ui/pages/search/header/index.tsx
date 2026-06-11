import { getSearchThemeClasses, HeroVariant } from "@/ui/util/searchTheme";

interface SearchDetailHeaderProps {
    title: string;
    subTitle: string;
    variant: HeroVariant;
    theme?: string;
    tagline?: string;
}

const SearchDetailHeader = ({
    title,
    subTitle,
    variant,
    theme,
    tagline,
}: SearchDetailHeaderProps) => {
    const {
        container,
        title: titleCls,
        subtitle: subtitleCls,
    } = getSearchThemeClasses(variant, theme);

    return (
        <header className="px-4 pt-6 pb-6 sm:px-6 lg:px-8">
            <div
                className={`mx-auto max-w-7xl rounded-hero-panel border border-highlight/20 shadow-hero px-6 py-10 sm:px-10 md:py-14 ${container}`}
            >
                {tagline && (
                    <p
                        className={`text-xs sm:text-sm font-semibold uppercase tracking-widest mb-2 font-dmSans ${subtitleCls}`}
                    >
                        {tagline}
                    </p>
                )}
                <h1
                    className={`text-2xl sm:text-3xl md:text-h1 font-bold font-urbanist-bold mb-1 sm:mb-2 ${titleCls}`}
                >
                    {title}
                </h1>
                <p
                    className={`text-sm sm:text-base md:text-body font-dmSans ${subtitleCls}`}
                >
                    {subTitle}
                </p>
            </div>
        </header>
    );
};

export default SearchDetailHeader;
