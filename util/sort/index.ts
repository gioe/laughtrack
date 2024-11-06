import { SortOptionInterface } from "../../objects/interfaces";
import { EntityType } from "../enum";
import { SortProperty } from "../enum";

export const getOptionsForEntityType = (type: EntityType): SortOptionInterface[] => {
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
        { name: "Most Popular", value: SortProperty.Popularity },
        { name: "A-Z", value: SortProperty.Alphabetical },
    ],
    CLUB: [
        { name: "Most Popular", value: SortProperty.Popularity },
        { name: "A-Z", value: SortProperty.Alphabetical },
    ],
    SHOW: [
        { name: "Date", value: SortProperty.Date },
        { name: "Most Popular", value: SortProperty.Popularity },
        { name: "Price: Low to High", value: SortProperty.LowToHigh },
        { name: "Price: High to Low", value: SortProperty.HighToLow },
    ],
};
