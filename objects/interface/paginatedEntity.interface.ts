import { ShowDTO } from "../class/show/show.interface"

export interface PaginatedEntityResponseDTO<T> {
    data: T[],
    total: number
}

export interface EntityResponseDTO<T> {
    data: T,
    shows: ShowDTO[]
    total: number
}
