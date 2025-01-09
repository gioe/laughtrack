import { Comedian } from "../../../../../objects/class/comedian/Comedian"
import { ComedianDTO } from "../../../../../objects/class/comedian/comedian.interface"
import { FilterDataDTO, PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../../../objects/interface"

export type ComedianSearchDTO = PaginatedEntityResponseDTO<ComedianDTO>
export type ComedianSearchData = PaginatedEntityResponse<Comedian>
export interface ComedianSearchResponse {
    data: ComedianSearchData
    filters: FilterDataDTO[] | undefined
}
