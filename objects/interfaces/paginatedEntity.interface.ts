import { Entity } from "./entity.interface"

export interface PaginatedEntityCollectionResponse {
    entities: Entity[]
    total: number
}

export interface PaginatedEntityResponse {
    entity: Entity
    total: number
}
