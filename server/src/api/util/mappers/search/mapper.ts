import { HomeSearchResultInterface } from "../../../../common/interfaces/searchResult.interface.js";
import { IHomeSearchResult } from "../../../../database/models.js";
import { orderShows } from "../../showUtil.js";
import { toShowDetailsInterfaceArray } from "../show/mapper.js";

export const toHomeSearchResultInterface = (payload: IHomeSearchResult, filter?: string): HomeSearchResultInterface => {
    const showDetialInterfaces = toShowDetailsInterfaceArray(payload.shows)
    return {
        city: payload.city,
        shows: orderShows(showDetialInterfaces)
    }
}
