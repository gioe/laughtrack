import { SortOptionInterface } from "../../objects/interface";
import { EntityType } from "../../objects/enum";
import { SortParamValue } from "../../objects/enum";

export const getSortOptionsForEntityType = (type: EntityType): SortOptionInterface[] => {
    switch (type) {
        case EntityType.Club: return SORT_OPTIONS.CLUB
        case EntityType.Show: return SORT_OPTIONS.SHOW
        case EntityType.Comedian: return SORT_OPTIONS.COMEDIAN
    }
}

export const getDefaultSortOptionForEntityType = (type: EntityType): SortParamValue => {
    switch (type) {
        case EntityType.Comedian: return SortParamValue.AlphabeticalAscending
        case EntityType.Club: return SortParamValue.AlphabeticalAscending
        case EntityType.Show: return SortParamValue.DateAscending
    }
}

const SORT_OPTIONS = {
    COMEDIAN: [
        { name: "A-Z", value: SortParamValue.AlphabeticalAscending },
        { name: "Z-A", value: SortParamValue.AlphabeticalDescending },
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending }
    ],
    CLUB: [
        { name: "A-Z", value: SortParamValue.AlphabeticalAscending, },
        { name: "Z-A", value: SortParamValue.AlphabeticalDescending },
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending },
    ],
    SHOW: [
        { name: "Date: Most Recent", value: SortParamValue.DateAscending },
        { name: "Date: Latest", value: SortParamValue.DateDescending },
        { name: "Most Popular", value: SortParamValue.PopularityDescending },
        { name: "Least Popular", value: SortParamValue.PopularityAscending },
        { name: "Price: Low to High", value: SortParamValue.PriceAscending },
        { name: "Price: High to Low", value: SortParamValue.PriceDescending },
        { name: "Scrape Date: Most Recent", value: SortParamValue.ScrapeDateDescending },
        { name: "Scrape Date: Latest", value: SortParamValue.ScrapeDateAscending },
    ],
};
