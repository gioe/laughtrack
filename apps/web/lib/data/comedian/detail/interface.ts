import { EntityResponseDTO } from "@/objects/interface/paginatedEntity.interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";

export interface ComedianDetailResponse extends EntityResponseDTO<ComedianDTO> {
    pastShows: ShowDTO[];
    pastShowsTotal: number;
    relatedComedians: ComedianDTO[];
}
