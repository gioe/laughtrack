import { Show } from "../../../objects/class/show/Show"
import { ShowDTO } from "../../../objects/class/show/show.interface"
import { EntityResponse, EntityResponseDTO } from "../../../objects/interface/paginatedEntity.interface"

export type ShowDetailDTO = EntityResponseDTO<ShowDTO>
export type ShowDetailPageData = EntityResponse<Show>
