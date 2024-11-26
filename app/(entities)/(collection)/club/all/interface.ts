import { Club } from "../../../../../objects/class/club/Club"
import { ClubDTO } from "../../../../../objects/class/club/club.interface"
import { PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../../../objects/interface"

export type AllClubPageDTO = PaginatedEntityResponseDTO<ClubDTO>
export type AllClubPageData = PaginatedEntityResponse<Club>
