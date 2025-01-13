import { Club } from "@/objects/class/club/Club"
import { ClubDTO } from "@/objects/class/club/club.interface"
import { FilterDataDTO } from "@/objects/interface"
import { EntityResponse, EntityResponseDTO } from "@/objects/interface/paginatedEntity.interface"

export type ClubDetailDTO = EntityResponseDTO<ClubDTO>
export type ClubDetailPageData = EntityResponse<Club>
export interface ClubDetailPageResponse {
    data: ClubDetailPageData
    filters: FilterDataDTO[] | undefined
}
