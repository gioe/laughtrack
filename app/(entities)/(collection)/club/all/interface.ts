import { Club } from "../../../../../objects/class/club/Club"
import { ClubDTO } from "../../../../../objects/class/club/club.interface"
import { PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../../../objects/interface"

export type ClubSearchDTO = PaginatedEntityResponseDTO<ClubDTO>
export type ClubSearchData = PaginatedEntityResponse<Club>
export interface ClubSearchResponse { data: ClubSearchData }
