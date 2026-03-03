import { ShowDTO } from "../class/show/show.interface"
import { FilterDTO } from "./filter.interface"

export interface PaginatedEntityResponseDTO<T> {
    data: T[],
    total: number,
    filters: FilterDTO[]

}

export interface EntityResponseDTO<T> {
    data: T,
    shows: ShowDTO[]
    total: number,
    filters: FilterDTO[]
}
