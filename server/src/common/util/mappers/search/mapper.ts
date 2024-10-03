import { HomeSearchResultInterface } from "../../../interfaces/client/searchResult.interface.js"
import { orderShows } from "../../showUtil.js"
import { toDates } from "../show/mapper.js"

export const toHomeSearchResultInterface = (payload: any, filter?: string): HomeSearchResultInterface => {
    const dates = toDates(payload.shows)
    return {
        city: payload.city,
        shows: orderShows(dates, filter)
    }
}
