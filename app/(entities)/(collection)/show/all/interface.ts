import { Show } from "../../../../../objects/class/show/Show"
import { ShowDTO } from "../../../../../objects/class/show/show.interface"
import { FilterDataDTO, PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../../../objects/interface"

export type ShowSearchDTO = PaginatedEntityResponseDTO<ShowDTO>
export type ShowSearchData = PaginatedEntityResponse<Show>
export interface ShowSearchResponse {
    data: ShowSearchData
    filters: FilterDataDTO[] | undefined
}
