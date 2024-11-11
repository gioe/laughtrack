export interface PaginatedResponseDTO<T> {
    response: {
        data: T[],
        total: number
    }
}
