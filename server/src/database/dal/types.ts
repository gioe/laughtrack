interface ListFilters {
    isDeleted?: boolean
    includeDeleted?: boolean
}

export interface GetAllShowsFilters extends ListFilters {}
export interface GetAllComediansFilters extends ListFilters {}
export interface GetAllClubsFilters extends ListFilters {}
