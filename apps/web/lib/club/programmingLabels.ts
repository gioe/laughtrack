import { FilterDTO } from "@/objects/interface";

export const MIXED_PROGRAMMING_FILTER_SLUG = "mixed_programming";

export const CLUB_PROGRAMMING_SHOW_TYPE_FILTER_SLUGS = [
    "standup",
    "improv",
    "theater",
    "music",
] as const;

export const CLUB_PROGRAMMING_CLUB_TYPE_FILTER_SLUGS = [
    "festival",
    "producer",
] as const;

const CLUB_PROGRAMMING_FILTERS = [
    { id: -9001, slug: "standup", name: "Stand-up clubs" },
    { id: -9002, slug: "improv", name: "Improv theaters" },
    { id: -9003, slug: "theater", name: "Theaters with comedy" },
    { id: -9004, slug: "music", name: "Music venues with comedy" },
    {
        id: -9005,
        slug: MIXED_PROGRAMMING_FILTER_SLUG,
        name: "Mixed comedy venues",
    },
    { id: -9006, slug: "festival", name: "Festivals" },
    { id: -9007, slug: "producer", name: "Producers" },
] as const satisfies readonly FilterDTO[];

export interface ClubProgrammingFields {
    clubType?: string | null;
    primaryShowType?: string | null;
    mixedProgramming?: boolean | null;
}

export function getClubProgrammingFilterOptions(
    activeFilters: string | null | undefined,
): FilterDTO[] {
    const selectedSlugs = new Set(parseFilterSlugs(activeFilters));
    return CLUB_PROGRAMMING_FILTERS.map((filter) => ({
        ...filter,
        selected: selectedSlugs.has(filter.slug),
    }));
}

export function getClubProgrammingLabel({
    clubType,
    primaryShowType,
    mixedProgramming,
}: ClubProgrammingFields): string {
    const normalizedClubType = normalizeValue(clubType);
    const normalizedShowType = normalizeValue(primaryShowType);

    if (normalizedClubType === "festival") return "Comedy festival";
    if (normalizedClubType === "producer") return "Comedy producer";
    if (mixedProgramming) return "Mixed comedy venue";

    switch (normalizedShowType) {
        case "standup":
            return normalizedClubType === "venue"
                ? "Stand-up comedy venue"
                : "Stand-up comedy club";
        case "improv":
            return "Improv theater";
        case "theater":
            return "Theater with comedy";
        case "music":
            return "Music venue with comedy";
        case "musical_comedy":
            return "Musical comedy venue";
        case "sketch":
            return "Sketch comedy venue";
        case "open_mic":
            return "Open mic comedy venue";
        case "podcast":
            return "Podcast taping venue";
        case "variety":
            return "Variety comedy venue";
        default:
            return normalizedClubType === "club"
                ? "Comedy club"
                : "Comedy venue";
    }
}

function normalizeValue(value: string | null | undefined): string {
    return value?.trim().toLowerCase() ?? "";
}

function parseFilterSlugs(filters: string | null | undefined): string[] {
    return filters
        ? filters
              .split(",")
              .map((slug) => slug.trim())
              .filter(Boolean)
        : [];
}
