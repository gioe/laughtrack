export type CreateShowDTO = {
    dateTime?: Date;
    ticketLink?: string;
    slug?: string;
}

export type FilterShowsDTO = {
    isDeleted?: boolean
    includeDeleted?: boolean
}