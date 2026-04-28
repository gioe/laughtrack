import { EntityResponseDTO } from "@/objects/interface/paginatedEntity.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

export interface ComedianDetailResponse extends EntityResponseDTO<ComedianDTO> {
    relatedComedians: ComedianDTO[];
}
