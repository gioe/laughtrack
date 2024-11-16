import { Show } from "../../../objects/class/show/Show"
import { ShowDTO } from "../../../objects/class/show/show.interface"
import { PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../objects/interface"

export type AllShowPageDTO = PaginatedEntityResponseDTO<ShowDTO>
export type AllShowPageData = PaginatedEntityResponse<Show>
