import { SortOptionInterface } from "../../objects/interfaces";
import { EntityType } from "../enum";
import { SortParamValue } from "../enum";

export const getSortOptionsForEntityType = (type: EntityType): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club:
            return SORT_OPTIONS.CLUB
        case EntityType.Show:
            return SORT_OPTIONS.SHOW
        case EntityType.Comedian:
            return SORT_OPTIONS.COMEDIAN
    }
}

const SORT_OPTIONS = {
    COMEDIAN: [
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending },
        { name: "A-Z", value: SortParamValue.AlphabeticalAscending },
        { name: "Z-A", value: SortParamValue.AlphabeticalDescending },
    ],
    CLUB: [
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending },
        { name: "A-Z", value: SortParamValue.AlphabeticalAscending },
        { name: "Z-A", value: SortParamValue.AlphabeticalDescending },
    ],
    SHOW: [
        { name: "Date: Most Recent", value: SortParamValue.DateAscending },
        { name: "Date: Oldest", value: SortParamValue.DateDescending },
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending },
        { name: "Price: Low to High", value: SortParamValue.PriceAscending },
        { name: "Price: High to Low", value: SortParamValue.PriceDescending },
        { name: "Scrape Date: Most Recent", value: SortParamValue.DateAscending },
        { name: "Scrape Date: Oldest", value: SortParamValue.DateDescending },
    ],
};
