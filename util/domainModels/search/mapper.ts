import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO, HomeSearchResultInterface } from "../../../interfaces"
import { toDates } from "../show/mapper"

export const toHomeSearchResultInterface = (payload: GetHomeSearchResultsResponseDTO, 
    comedianFilters?: string, showFilters?: 
    string, sort?: string): HomeSearchResultInterface => {
    return {
        city: payload.city,
        shows: toDates(payload.dates)
    }
}

export const toGetHomeSearchResultsDTO = (payload: any): GetHomeSearchResultsDTO => {
    return {
        location: payload.location,
        start_date: payload.startDate,
        end_date: payload.endDate
    }
}
