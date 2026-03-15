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
        <header className={`text-center py-16 md:py-20 px-4 ${container}`}>
            <h1
                className={`text-2xl sm:text-3xl md:text-[32px] font-bold font-gilroy-bold mb-1 sm:mb-2 ${titleCls}`}
            >
                {title}
            </h1>
            {tagline && (
                <p
                    className={`text-sm sm:text-base mb-1 font-dmSans ${subtitleCls}`}
                >
                    {tagline}
                </p>
            )}
            <p
                className={`text-sm sm:text-base md:text-[16px] font-dmSans ${subtitleCls}`}
            >
                {subTitle}
            </p>
        </header>
    );
};

export default SearchDetailHeader;
