import { SortOptionInterface } from "../../objects/interface";
import { EntityType} from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

export const getSortOptionsForEntityType = (type: EntityType): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club:
            return [
                { name: "A-Z", value: SortParamValue.NameAsc,},
                { name: "Z-A", value: SortParamValue.NameDesc}
                // { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                // { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending },
            ]
        case EntityType.Comedian:
            return [
                { name: "A-Z", value: SortParamValue.NameAsc},
                { name: "Z-A", value: SortParamValue.NameDesc },
                { name: "Most Active", value: SortParamValue.ActivityAsc },
                { name: "Least Active", value: SortParamValue.ActivityDesc},
                { name: "Most Popular", value: SortParamValue.PopularityAsc },
                { name: "Least Popular", value: SortParamValue.PopularityDesc },
            ]
        default:
                return [
                    { name: "Earliest Date", value: SortParamValue.DateAsc },
                    { name: "Latest Date", value: SortParamValue.DateDesc },
                    { name: "Most Popular", value: SortParamValue.PopularityAsc },
                    { name: "Least Popular", value: SortParamValue.PopularityDesc },
                    { name: "$$: Low to High", value: SortParamValue.PriceAsc},
                    { name: "$$: High to Low", value: SortParamValue.PriceDesc },
                ]
    }
}
