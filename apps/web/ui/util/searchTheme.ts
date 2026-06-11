export type SearchTheme = "brand" | "dark" | "warm";
export type HeroVariant = "comedian" | "club" | "show" | "podcast";

interface HeroThemeClasses {
    container: string;
    title: string;
    subtitle: string;
}

const VALID_THEMES = new Set<SearchTheme>(["brand", "dark", "warm"]);

// Hero washes mirror the iOS LaughTrackTheme hero gradient: a mostly-dark
// canvas that blooms into copper toward the bottom-right, with warm cream
// text. All entity variants share one treatment so the four search pages
// read as one family.
const THEME_CLASSES: Record<SearchTheme, HeroThemeClasses> = {
    brand: {
        container: "bg-gradient-to-br from-canvas via-cedar to-copper",
        title: "text-foreground",
        subtitle: "text-foreground/75",
    },
    dark: {
        container:
            "bg-gradient-to-br from-canvas via-cedar-dark to-copper-dark",
        title: "text-foreground",
        subtitle: "text-muted-foreground",
    },
    warm: {
        container: "bg-gradient-to-br from-cedar via-brown-rust to-copper",
        title: "text-foreground",
        subtitle: "text-foreground/75",
    },
};

export function getSearchThemeClasses(
    _variant: HeroVariant,
    theme: string | undefined,
): HeroThemeClasses {
    const key: SearchTheme = VALID_THEMES.has(theme as SearchTheme)
        ? (theme as SearchTheme)
        : "brand";
    return THEME_CLASSES[key];
}
