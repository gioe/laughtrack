import { Entity } from "./entity.interface"

// Client
export interface PaginatedEntityResponse<T extends Entity> {
    entities: T[]
    total: number
}

export interface EntityResponse<T extends Entity> {
    entity: T
    total: number
}

// DB
export interface PaginatedEntityResponseDTO<T> {
    response: PaginatedEntityDTO<T[]>
}

export interface EntityResponseDTO<T> {
    response: PaginatedEntityDTO<T>
}

export interface PaginatedEntityDTO<T> {
    data: T,
    total: number
}
