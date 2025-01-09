import { Comedian } from "../../../../../objects/class/comedian/Comedian"
import { ComedianDTO } from "../../../../../objects/class/comedian/comedian.interface"
import { FilterDataDTO } from "../../../../../objects/interface"
import { EntityResponse, EntityResponseDTO } from "../../../../../objects/interface/paginatedEntity.interface"

export type ComedianDetailDTO = EntityResponseDTO<ComedianDTO>
export type ComedianDetailPageData = EntityResponse<Comedian>
export interface ComedianDetailPageResponse {
    data: ComedianDetailPageData
    filters: FilterDataDTO[] | undefined

}
