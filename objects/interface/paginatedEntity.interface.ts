import { Entity } from "./entity.interface"

// Client
export interface PaginatedEntityCollectionResponse<T extends Entity> {
    entities: T[]
    total: number
}

export interface PaginatedEntityResponse<T extends Entity> {
    entity: T
    total: number
}

// DB
export interface PaginatedEntityResponseDTO<T> {
    response: PaginatedEntityDTO<T>
}

export interface PaginatedEntityCollectionResponseDTO<T> {
    response: PaginatedEntityDTO<T[]>
}

export interface PaginatedEntityDTO<T> {
    data: T,
    total: number
}
