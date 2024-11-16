import { SortOptionInterface } from "../../objects/interface";
import { EntityType, DirectionParamValue } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

export const getSortOptionsForEntityType = (type: EntityType): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club:
            return [
                { name: "A-Z", value: SortParamValue.Name, direction: DirectionParamValue.Ascending },
                { name: "Z-A", value: SortParamValue.Name, direction: DirectionParamValue.Descending },
                { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending }
            ]
        case EntityType.Show:
            return [
                { name: "Date: Most Recent", value: SortParamValue.Date, direction: DirectionParamValue.Ascending },
                { name: "Date: Latest", value: SortParamValue.Date, direction: DirectionParamValue.Descending },
                { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending },
                { name: "Price: Low to High", value: SortParamValue.Price, direction: DirectionParamValue.Ascending },
                { name: "Price: High to Low", value: SortParamValue.Price, direction: DirectionParamValue.Descending },
                { name: "Scrape Date: Most Recent", value: SortParamValue.ScrapeDate, direction: DirectionParamValue.Ascending },
                { name: "Scrape Date: Latest", value: SortParamValue.ScrapeDate, direction: DirectionParamValue.Descending },
            ]
        case EntityType.Comedian:
            return [
                { name: "A-Z", value: SortParamValue.Name, direction: DirectionParamValue.Ascending },
                { name: "Z-A", value: SortParamValue.Name, direction: DirectionParamValue.Descending },
                { name: "Most Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Descending },
                { name: "Least Popular", value: SortParamValue.Popularity, direction: DirectionParamValue.Ascending }
            ]
    }
}
