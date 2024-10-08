import { HomeSearchResultInterface } from "../../../interfaces/client/searchResult.interface.js"
import { GetHomeSearchResultsResponseDTO } from "../../../interfaces/data/search.interface.js"
import { orderShows } from "../../showUtil.js"
import { toDates } from "../show/mapper.js"

export const toHomeSearchResultInterface = (payload: GetHomeSearchResultsResponseDTO, sort?: string): HomeSearchResultInterface => {
    return {
        city: payload.city,
        dates: toDates(payload.dates, sort)
    }
}
