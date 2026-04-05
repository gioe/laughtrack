export type SearchTheme = "brand" | "dark" | "warm";
export type HeroVariant = "comedian" | "club" | "show";

interface HeroThemeClasses {
    container: string;
    title: string;
    subtitle: string;
}

const VALID_THEMES = new Set<SearchTheme>(["brand", "dark", "warm"]);

const THEME_CLASSES: Record<
    HeroVariant,
    Record<SearchTheme, HeroThemeClasses>
> = {
    comedian: {
        brand: {
            container: "bg-gradient-to-br from-cedar to-copper",
            title: "text-white",
            subtitle: "text-white/80",
        },
        dark: {
            container:
                "bg-gradient-to-br from-gray-900 via-[#2A1208] to-[#8B5523]",
            title: "text-white",
            subtitle: "text-gray-300",
        },
        warm: {
            container: "bg-gradient-to-br from-amber-700 to-[#B95D3B]",
            title: "text-white",
            subtitle: "text-amber-100",
        },
    },
    club: {
        brand: {
            container: "bg-gradient-to-r from-cedar to-copper",
            title: "text-white",
            subtitle: "text-white/80",
        },
        dark: {
            container:
                "bg-gradient-to-r from-gray-900 via-[#2A1208] to-[#8B5523]",
            title: "text-white",
            subtitle: "text-gray-300",
        },
        warm: {
            container: "bg-gradient-to-r from-amber-700 to-[#B95D3B]",
            title: "text-white",
            subtitle: "text-amber-100",
        },
    },
    show: {
        brand: {
            container: "bg-gradient-to-br from-cedar to-copper",
            title: "text-white",
            subtitle: "text-white/80",
        },
        dark: {
            container:
                "bg-gradient-to-br from-gray-900 via-[#2A1208] to-[#8B5523]",
            title: "text-white",
            subtitle: "text-gray-300",
        },
        warm: {
            container: "bg-gradient-to-br from-amber-700 to-[#B95D3B]",
            title: "text-white",
            subtitle: "text-amber-100",
        },
    },
};

export function getSearchThemeClasses(
    variant: HeroVariant,
    theme: string | undefined,
): HeroThemeClasses {
    const key: SearchTheme = VALID_THEMES.has(theme as SearchTheme)
        ? (theme as SearchTheme)
        : "brand";
    return THEME_CLASSES[variant][key];
}
