import { SortOptionInterface } from "../../objects/interface";
import { EntityType } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

// Shared tail appended to every entity's sort list so users see the same
// "Most Popular / Least Popular / A-Z / Z-A" controls regardless of which
// search page they're on. Entity-specific options are prepended above.
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
            return [
                { name: "Most Active", value: SortParamValue.TotalShowsDesc },
                { name: "Least Active", value: SortParamValue.TotalShowsAsc },
                ...COMMON_SORT_OPTIONS,
            ];
        case EntityType.Comedian: {
            // Lead with the common tail so options[0] stays "Most Popular" —
            // middleware enforces PopularityDesc as the default sort for
            // comedians, and useSortParams treats options[0] as the UI default.
            const base: SortOptionInterface[] = [
                ...COMMON_SORT_OPTIONS,
                {
                    name: "Most Upcoming Shows",
                    value: SortParamValue.ShowCountDesc,
                },
                {
                    name: "Fewest Upcoming Shows",
                    value: SortParamValue.ShowCountAsc,
                },
                { name: "Most Active", value: SortParamValue.ActivityDesc },
                { name: "Least Active", value: SortParamValue.ActivityAsc },
            ];
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
            return [
                { name: "A-Z", value: SortParamValue.NameAsc },
                { name: "Z-A", value: SortParamValue.NameDesc },
                { name: "Recently Updated", value: SortParamValue.ActivityDesc },
                { name: "Oldest Updated", value: SortParamValue.ActivityAsc },
                { name: "Most Episodes", value: SortParamValue.ShowCountDesc },
                { name: "Fewest Episodes", value: SortParamValue.ShowCountAsc },
                { name: "Newest First", value: SortParamValue.InsertedAtDesc },
                { name: "Oldest First", value: SortParamValue.InsertedAtAsc },
            ];
        default:
            return [
                { name: "Earliest Date", value: SortParamValue.DateAsc },
                { name: "Latest Date", value: SortParamValue.DateDesc },
                { name: "$$: Low to High", value: SortParamValue.PriceAsc },
                { name: "$$: High to Low", value: SortParamValue.PriceDesc },
                ...COMMON_SORT_OPTIONS,
            ];
    }
};
