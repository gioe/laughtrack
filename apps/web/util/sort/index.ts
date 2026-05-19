import { SortOptionInterface } from "../../objects/interface";
import { EntityType } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

// Web sort options are kept aligned with the iOS app's per-entity option sets
// so users moving between platforms see the same axes. Scraping-derived axes
// (e.g. "Recently Updated" = Podcast.updated_at, which tracks our scraper's
// metadata refresh and NOT release cadence; "Newest First" = createdAt, which
// tracks when we first ingested the row) are intentionally not exposed —
// they're behind-the-scenes signal that doesn't map to anything the user
// would expect from the label. Activity/freshness sorts can return once we
// have a real user-facing axis backing them (e.g. a denormalized
// latest_episode_at column).
//
// Reference iOS enums: PrimitiveSortOption, ShowSortOption, ClubSortOption,
// PodcastSortOption in ios/Sources/LaughTrackApp/Search/Models/SearchOptions.swift.

const COMMON_SORT_OPTIONS: SortOptionInterface[] = [
    { name: "Most Popular", value: SortParamValue.PopularityDesc },
    { name: "Least Popular", value: SortParamValue.PopularityAsc },
    { name: "A-Z", value: SortParamValue.NameAsc },
    { name: "Z-A", value: SortParamValue.NameDesc },
];

export const getSortOptionsForEntityType = (
    type: EntityType,
    isAdmin = false,
): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club:
            // Matches iOS ClubSortOption: mostActive, leastActive, +common.
            return [
                { name: "Most Active", value: SortParamValue.TotalShowsDesc },
                { name: "Least Active", value: SortParamValue.TotalShowsAsc },
                ...COMMON_SORT_OPTIONS,
            ];
        case EntityType.Comedian: {
            // Matches iOS PrimitiveSortOption: 4 options.
            // (Admin-only Newest/Oldest extras remain for ops, behind isAdmin.)
            const base: SortOptionInterface[] = [...COMMON_SORT_OPTIONS];
            if (isAdmin) {
                base.push(
                    {
                        name: "Newest First",
                        value: SortParamValue.InsertedAtDesc,
                    },
                    {
                        name: "Oldest First",
                        value: SortParamValue.InsertedAtAsc,
                    },
                );
            }
            return base;
        }
        case EntityType.Podcast:
            // Matches iOS PodcastSortOption: mostEpisodes, fewestEpisodes, A-Z, Z-A.
            // First entry is the UI default, mirroring iOS .mostEpisodes.
            return [
                { name: "Most Episodes", value: SortParamValue.ShowCountDesc },
                { name: "Fewest Episodes", value: SortParamValue.ShowCountAsc },
                { name: "A-Z", value: SortParamValue.NameAsc },
                { name: "Z-A", value: SortParamValue.NameDesc },
            ];
        default:
            // Matches iOS ShowSortOption: earliest, latest, popular, budget, premium.
            return [
                { name: "Earliest Date", value: SortParamValue.DateAsc },
                { name: "Latest Date", value: SortParamValue.DateDesc },
                { name: "Most Popular", value: SortParamValue.PopularityDesc },
                { name: "$$: Low to High", value: SortParamValue.PriceAsc },
                { name: "$$: High to Low", value: SortParamValue.PriceDesc },
            ];
    }
};
