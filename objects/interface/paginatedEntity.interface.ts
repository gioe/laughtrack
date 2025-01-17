export interface PaginatedEntityResponseDTO<T> {
    data: T[],
    total: number
}

export interface EntityResponseDTO<T> {
    data: T,
    total: number
}
