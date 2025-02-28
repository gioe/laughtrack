import { SortOptionInterface } from "../../objects/interface";
import { EntityType, DirectionParamValue } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

export const getSortOptionsForEntityType = (type: EntityType | undefined): SortOptionInterface[] => {
    if (type == undefined) return [];
    switch (type) {
        case EntityType.Club:
            return [
                { name: "A-Z", value: SortParamValue.Name, direction: DirectionParamValue.Ascending },
                { name: "Z-A", value: SortParamValue.Name, direction: DirectionParamValue.Descending }
                // { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                // { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending },
            ]
        case EntityType.Show:
            return [
                { name: "Earliest Date", value: SortParamValue.Date, direction: DirectionParamValue.Ascending },
                { name: "Latest Date", value: SortParamValue.Date, direction: DirectionParamValue.Descending },
                { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending },
                { name: "$$: Low to High", value: SortParamValue.Price, direction: DirectionParamValue.Ascending },
                { name: "$$: High to Low", value: SortParamValue.Price, direction: DirectionParamValue.Descending },
            ]
        case EntityType.Comedian:
            return [
                { name: "A-Z", value: SortParamValue.Name, direction: DirectionParamValue.Ascending },
                { name: "Z-A", value: SortParamValue.Name, direction: DirectionParamValue.Descending },
                { name: "Most Active", value: SortParamValue.Activity, direction: DirectionParamValue.Descending },
                { name: "Least Active", value: SortParamValue.Activity, direction: DirectionParamValue.Ascending },
                { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending },
            ]
    }
}
