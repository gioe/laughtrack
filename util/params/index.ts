import { SearchParams } from "../../objects/interfaces";
import { SortParamValue } from "../enum";


export const getOrderClauseFromParams = (params?: SearchParams) => {
    switch (params?.sort as SortParamValue) {
        case SortParamValue.AlphabeticalAscending: return "date_time ASC"
        case SortParamValue.AlphabeticalDescending: return "date_time DESC"
        case SortParamValue.DateDescending: return "date_time DESC"
        case SortParamValue.PopularityAscending: return "popularity ASC"
        case SortParamValue.PopularityDescending: return "popularity DESC"
        case SortParamValue.PriceAscending: return "price ASC"
        case SortParamValue.PriceDescending: return "price DESC"
        case SortParamValue.ScrapeDateAscending: return "last_scrape_date ASC"
        case SortParamValue.ScrapeDateDescending: return "last_scrape_date DESC"
        default: return "date_time ASC"

    }

}
