import { HomeSearchResultInterface } from "../../../interfaces/client/searchResult.interface.js"
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from "../../../interfaces/data/search.interface.js"
import { toDates } from "../show/mapper.js"

export const toHomeSearchResultInterface = (payload: GetHomeSearchResultsResponseDTO, comedianFilters?: string, showFilters?: string, sort?: string): HomeSearchResultInterface => {
    return {
        city: payload.city,
        dates: toDates(payload.dates),
        clubs: payload.clubs
    }
}

export const toGetHomeSearchResultsDTO = (payload: any): GetHomeSearchResultsDTO => {
    return {
        location: payload.location,
        start_date: payload.startDate,
        end_date: payload.endDate,
        comedians: payload.query == '' ? undefined : payload.query,
        clubs: payload.clubs == '' ? undefined : payload.clubs,
        sort: payload.sort == '' ? undefined : payload.sort
    }
}
