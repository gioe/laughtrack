import { Comedian } from "../../../objects/class/comedian/Comedian"
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface"
import { PaginatedEntityResponse, PaginatedEntityResponseDTO } from "../../../objects/interface"

export type AllComedianPageDTO = PaginatedEntityResponseDTO<ComedianDTO>
export type AllComedianPageData = PaginatedEntityResponse<Comedian>
