import { ClubDTO } from "@/objects/class/club/club.interface"
import { FilterDataDTO, PaginatedEntityResponseDTO } from "@/objects/interface"

export type ClubSearchResponse = PaginatedEntityResponseDTO<ClubDTO>

export interface GetFiltersResponse {
    filters: FilterDataDTO[]
}
