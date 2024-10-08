import { HomeSearchResultInterface } from "../../../interfaces/client/searchResult.interface.js"
import { GetHomeSearchResultsResponseDTO } from "../../../interfaces/data/search.interface.js"
import { orderShows } from "../../showUtil.js"
import { toDates } from "../show/mapper.js"

export const toHomeSearchResultInterface = (payload: GetHomeSearchResultsResponseDTO, sort?: string): HomeSearchResultInterface => {
    const dates = toDates(payload.dates)
    return {
        city: payload.city,
        shows: orderShows(dates, sort)
    }
}
