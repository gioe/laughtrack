import { SortOptionInterface } from "../../objects/interface";
import { EntityType } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

export const getSortOptionsForEntityType = (
    type: EntityType,
    isAdmin = false,
): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club:
            return [
                { name: "Most Active", value: SortParamValue.TotalShowsDesc },
                { name: "Least Active", value: SortParamValue.TotalShowsAsc },
                { name: "A-Z", value: SortParamValue.NameAsc },
                { name: "Z-A", value: SortParamValue.NameDesc },
            ];
        case EntityType.Comedian: {
            const base: SortOptionInterface[] = [
                { name: "Most Popular", value: SortParamValue.PopularityDesc },
                { name: "Least Popular", value: SortParamValue.PopularityAsc },
                {
                    name: "Most Upcoming Shows",
                    value: SortParamValue.ShowCountDesc,
                },
                {
                    name: "Fewest Upcoming Shows",
                    value: SortParamValue.ShowCountAsc,
                },
                { name: "A-Z", value: SortParamValue.NameAsc },
                { name: "Z-A", value: SortParamValue.NameDesc },
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
        default:
            return [
                { name: "Earliest Date", value: SortParamValue.DateAsc },
                { name: "Latest Date", value: SortParamValue.DateDesc },
                { name: "Most Popular", value: SortParamValue.PopularityDesc },
                { name: "Least Popular", value: SortParamValue.PopularityAsc },
                { name: "$$: Low to High", value: SortParamValue.PriceAsc },
                { name: "$$: High to Low", value: SortParamValue.PriceDesc },
            ];
    }
};
