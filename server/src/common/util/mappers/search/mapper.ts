import { HomeSearchResultInterface } from "../../../interfaces/client/searchResult.interface.js"
import { GetHomeSearchResultsResponseDTO } from "../../../interfaces/data/search.interface.js"
import { toDates } from "../show/mapper.js"

export const toHomeSearchResultInterface = (payload: GetHomeSearchResultsResponseDTO, filter?: string, sort?: string): HomeSearchResultInterface => {
    return {
        city: payload.city,
        dates: toDates(payload.dates, filter, sort)
    }
}
